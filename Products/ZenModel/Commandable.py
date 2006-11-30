#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""Commandable

Mixin class for classes that need a relationship back from UserCommand.

"""

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from UserCommand import UserCommand
from Acquisition import aq_base, aq_parent, aq_chain
from Products.PageTemplates.Expressions import getEngine
from Products.ZenUtils.ZenTales import talesCompile
from DateTime import DateTime
import os
import popen2
import fcntl
import select
import signal
import time
import cgi
import sys
import traceback

import logging
log = logging.getLogger("zen.Device")

class Commandable:

    defaultTimeout = 60 # seconds

    security = ClassSecurityInfo()

    security.declareProtected('Change Device', 'manage_addUserCommand')
    def manage_addUserCommand(self, newId=None, REQUEST=None):
        "Add a UserCommand to this device"
        uc = None
        if newId:
            uc = UserCommand(newId)
            self.userCommands._setObject(newId, uc)
            if self.meta_type == 'Device':
                self.setLastChange()
        if REQUEST:
            if uc:
                REQUEST['message'] = "Command Added"
                url = '%s/userCommands/%s' % (self.getPrimaryUrlPath(), uc.id)
                #url = uc.getPrimaryUrlPath()
                REQUEST['RESPONSE'].redirect(url)
            return self.callZenScreen(REQUEST)

         
    security.declareProtected('Change Device', 'manage_deleteUserCommand')
    def manage_deleteUserCommand(self, delids=(), REQUEST=None):
        "Delete User Command(s) to this device"
        import types
        if type(delids) in types.StringTypes:
            delids = [delids]
        for id in delids:
            self.userCommands._delObject(id)
        if self.meta_type == 'Device':            
            self.setLastChange()
        if REQUEST:
            REQUEST['message'] = "Command(s) Deleted"
            return self.callZenScreen(REQUEST)


    def manage_editUserCommand(self, commandId, REQUEST=None):
        ''' Want to redirect back to management tab after a save
        '''
        command = self.getUserCommand(commandId)
        if command:
            command.manage_changeProperties(**REQUEST.form)
        # Try to dig up a management tab from the factory information.
        # If we can't find it then just stay on the edit page.
        actions = [a for a in self.factory_type_information[0]['actions'] 
                if a['name'] == 'Manage']
        if actions:
            url = '%s/%s?commandId=%s' % (self.getPrimaryUrlPath(), 
                                        actions[0]['action'], command.id)
            REQUEST.RESPONSE.redirect(url)
        else:
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'manage_doUserCommand')
    def manage_doUserCommand(self, commandId=None, REQUEST=None):
        ''' Perform the given usercommand
        '''
        self.doCommand(self, commandId, REQUEST)


    security.declareProtected('Change Device', 'getUserCommands')
    def getUserCommands(self, context=None, asDict=False):
        ''' Get the user commands available in this context
        '''
        commands = {}
        if not context:
            context = self
        mychain = aq_chain(context)
        mychain.reverse()
        for obj in mychain:
            if getattr(aq_base(obj), 'userCommands', None):
                for c in obj.userCommands():
                    commands[c.id] = c
        def cmpCommands(a, b):
            return cmp(a.getId(), b.getId())
        if not asDict:
            commands = commands.values()
            commands.sort(cmpCommands)
        return commands


    def getUserCommand(self, commandId):
        ''' Returns the command from the current context if it exists
        '''
        return self.getUserCommands(asDict=True).get(commandId, None)


    def doCommand(self, context, commandId, REQUEST=None):
        ''' Execute a UserCommand on a single device if deviceId,
        a single service if serviceId or all devices/services
        in this container. If REQUEST then
        wrap output in proper zenoss html page.
        '''
        # This could be changed so that output is sent through a
        # logger so that non web-based code can produce output.
        # Not necessary for now.
        command = self.getUserCommands(context, asDict=True)[commandId]
        if REQUEST:
            REQUEST['cmd'] = command
            header, footer = self.commandOutputTemplate().split('OUTPUT_TOKEN')
            REQUEST.RESPONSE.write(header)
            out = REQUEST.RESPONSE
        else:
            out = None
        
        startTime = time.time()
        numTargets = 0
        for target in self.getUserCommandTargets():
            numTargets += 1
            try:
                self.write(out, '')
                self.write(out, '==== %s ====' % target.id)
                self.doCommandForTarget(command, context, target, out)
            except:
                self.write(out,
                    'exception while performing command for %s' % target.id)
                self.write(
                    out, 'type: %s  value: %s' % tuple(sys.exc_info()[:2]))
                self.write(out, 'traceback:')
                self.write(out,traceback.format_list(traceback.extract_tb(sys.exc_info()[2])))
            self.write(out, '')
        self.write(out, '')
        self.write(out, 'DONE in %s seconds on %s targets' % 
                    (long(time.time() - startTime), numTargets))
        REQUEST.RESPONSE.write(footer)

        
    def doCommandForTarget(self, cmd, context, target, out):
        ''' Execute the given UserCommand on the given target and context.
        '''
        compiled = self.compile(cmd, context, target)
        child = popen2.Popen4(compiled)
        flags = fcntl.fcntl(child.fromchild, fcntl.F_GETFL)
        fcntl.fcntl(child.fromchild, fcntl.F_SETFL, flags | os.O_NDELAY)
        timeout = getattr(target, 'zCommandCommandTimeout', self.defaultTimeout)
        endtime = time.time() + max(timeout, 1)
        self.write(out, '%s' % compiled)
        self.write(out, '')
        while time.time() < endtime and child.poll() == -1:
            readable, writable, errors = \
                                select.select([child.fromchild], [], [], 1)
            if readable:
                self.write(out, child.fromchild.read())
        if child.poll() == -1:
            self.write(out, 'Command timed out for %s' % target.id +
                            ' (timeout is %s seconds)' % timeout)
            os.kill(child.pid, signal.SIGKILL)


    def compile(self, cmd, context, target):
        ''' Evaluate command as a tales expression with the given context
        '''
        exp = "string:"+ cmd.command
        compiled = talesCompile(exp)
        environ = target.getUserCommandEnvironment(context)
        res = compiled(getEngine().getContext(environ))
        if isinstance(res, Exception):
            raise res
        return res

    
    def getUserCommandEnvironment(self, context):
        ''' Get the environment that provides context for the tales
        evaluation of a UserCommand.
        '''
        # Overridden by Service and Device
        return {
                'target': self,
                'here': context, 
                'nothing': None,
                'now': DateTime()
                }
    

    def getUserCommandTargets(self):
        ''' Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        '''
        raise 'must be implemented by subclass'


    def write(self, out, lines):
        ''' Output (maybe partial) result text from a UserCommand.
        '''
        # Looks like firefox renders progressive output more smoothly
        # if each line is stuck into a table row.  
        startLine = '<tr><td class="tablevalues">'
        endLine = '</td></tr>\n'
        if out:
            if not isinstance(lines, list):
                lines = [lines]
            for l in lines:
                if not isinstance(l, str):
                    l = str(l)
                l = l.strip()
                l = cgi.escape(l)
                l = l.replace('\n', endLine + startLine)
                out.write(startLine + l + endLine)

InitializeClass(Commandable)
