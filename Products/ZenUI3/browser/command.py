########################################################################### 
# 
# This program is part of Zenoss Core, an open source monitoring platform. 
# Copyright (C) 2010, Zenoss Inc. 
# 
# This program is free software; you can redistribute it and/or modify it 
# under the terms of the GNU General Public License version 2 as published by 
# the Free Software Foundation. 
# 
# For complete information please visit: http://www.zenoss.com/oss/ 
# 
########################################################################### 
import os
import shlex
import sys
import subprocess
import signal
import time
from Products.ZenUI3.browser.streaming import StreamingView, StreamClosed
from Products.ZenUtils.jsonutils import unjson

class CommandView(StreamingView):
    """
    Accepts a POST request with a 'data' field containing JSON representing
    the command to be run and the uids of the devices against which to run it.

    Designed to work in concert with the Ext component Zenoss.CommandWindow.
    """
    def stream(self):
        data = unjson(self.request.get('data'))
        command = self.context.getUserCommands(asDict=True).get(data['command'], None)
        if command:
            for uid in data['uids']:
                target = self.context.unrestrictedTraverse(uid)
                self.execute(command, target)

    def execute(self, cmd, target):
        try:
            compiled = self.context.compile(cmd, target)

            timeout = getattr(target, 'zCommandCommandtimeout',
                              self.context.defaultTimeout)
            end = time.time() + timeout
            self.write('==== %s ====' % target.titleOrId())
            self.write(compiled)

            p = subprocess.Popen(shlex.split(compiled),
                                 bufsize=1,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
            retcode = None
            while time.time() < end:
                while True:
                    line = p.stdout.readline()
                    if not line: break
                    try:
                        self.write(line)
                    except StreamClosed:
                        # FIXME: In Python 2.6, use p.terminate() or p.kill()
                        os.kill(p.pid, signal.SIGKILL)
                        raise
                retcode = p.poll()
                if retcode is not None:
                    break
            else:
                # FIXME: In Python 2.6, use p.terminate() or p.kill()
                os.kill(p.pid, signal.SIGKILL)
                self.write('Command timed out for %s (timeout is %s seconds)'%(
                                target.titleOrId(), timeout)
                          )
        except:
            self.write('Exception while performing command for %s' %
                       target.id)
            self.write('Type: %s   Value: %s' % tuple(sys.exc_info()[:2]))

            
class TestDataSourceView(StreamingView):
    """
    Accepts a post with data in of the command to be tested against a device
    """

    def stream(self):
        """
        Called by the parent class, this method asks the datasource
        to test itself.
        """
        request = self.request
        context = self.context
        request['renderTemplate'] = False
        return context.testDataSourceAgainstDevice(request.get('testDevice'), request, self.write, self.reportError)
        
    def reportError(self, title, body, priority=None, image=None):
        """
        If something goes wrong, just display it in the command output (as opposed to a browser message)
        """
        error = "<b>%s</b><p>%s</p>" % (title, body)
        return self.write(error)
