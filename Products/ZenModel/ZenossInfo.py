import os
import re
import logging
log = logging.getLogger("zen.ZenossInfo")

import transaction
from Globals import InitializeClass
from OFS.SimpleItem import SimpleItem
from AccessControl import ClassSecurityInfo
from OFS.PropertyManager import PropertyManager

from Products.ZenModel.version import Current

def manage_addZenossInfo(context, id='ZenossInfo', REQUEST=None):
    """
    Provide an instance of ZenossInfo for the portal.
    """
    about = ZenossInfo(id)
    about.id = 'About'
    try:
        context._getOb(id)
    except AttributeError:
        context._setObject(id, about)

    if REQUEST is not None:
        REQUEST.RESPONSE.redirect(context.absolute_url() +'/manage_main')

class ZenossInfo(SimpleItem, PropertyManager):

    security = ClassSecurityInfo()

    _properties = (
        {'id':'id', 'type':'string'},
        {'id':'title', 'type':'string'},
    )

    def getAllVersions(self):
        """
        Return a list of version numbers for currently tracked component
        software.
        """
        vers = Current.getVersions()
        versions = [
            {'header': 'Zenoss', 'data': vers['Zenoss']},
            {'header': 'OS', 'data': vers['OS']},
            {'header': 'Zope', 'data': vers['Zope']},
            {'header': 'Python', 'data': vers['Python']},
            {'header': 'Database', 'data': vers['Database']},
            {'header': 'RRD', 'data': vers['RRD']},
            {'header': 'Twisted', 'data': vers['Twisted']},
            {'header': 'SNMP', 'data': vers['SNMP']},
        ]
        return versions
    security.declareProtected('View','getAllVersions')

    def getAllUptimes(self):
        """
        Return a list of daemons with their uptimes.
        """
        app = self.getPhysicalRoot()
        uptimes = []
        zope = {
            'header': 'Zope',
            'data': app.Control_Panel.process_time(),
        }
        uptimes.append(zope)
        return uptimes
    security.declareProtected('View','getAllUptimes')

    def getZenossDaemonStates(self):
        """
        Return a data structures representing the states of the supported
        Zenoss daemons.
        """
        states = []
        activeButtons = {'button1': 'Restart', 'button2': 'Stop', 'button2state': True}
        inactiveButtons = {'button1': 'Start', 'button2': 'Stop', 'button2state': False}
        for daemon in self._getDaemonList():
            pid = self._getDaemonPID(daemon)
            if pid:
                buttons = activeButtons
                msg = 'Up'
                color = '#0F0'
            else:
                buttons = inactiveButtons
                msg = 'Down'
                color = '#F00'
            states.append({
                'name': daemon,
                'pid': pid,
                'msg': msg,
                'color': color,
                'buttons': buttons})
        return states

    def _getDaemonPID(self, name):
        """
        For a given daemon name, return its PID from a .pid file.
        """
        if name == 'zopectl':
            name = 'Z2'
        elif name == 'zeoctl':
            name = 'ZEO'
        pidFile = os.path.join(os.getenv('ZENHOME'), 'var', '%s.pid' % name)
        if os.path.exists(pidFile):
            pid = open(pidFile).read()
        else:
            pid = None
        return pid

    def _getDaemonList(self):
        """
        Get the list of supported Zenoss daemons.
        """
        masterScript = os.path.join(os.getenv('ZENHOME'), 'bin', 'zenoss')
        daemons = []
        for line in open(masterScript).readlines():
            match = re.match('C="\$C (.*)"$', line)
            if match:
                daemons.append(match.groups()[0])
        return daemons

    def manage_daemonAction(self, REQUEST=None):
        """
        Start, stop, or restart Zenoss daemons from a web interface.
        """
        # XXX
        # this exception is for testing purposes only
        raise 'Problem! :' + str(REQUEST.form)
        if not REQUEST:
            return self.callZenScreen(REQUEST)
        legalValues = ['start', 'restart', 'stop']
        action = (REQUEST.form.get('action') or '').lower()
        if action not in legalValues:
            return self.callZenScreen(REQUEST)
        daemon = os.path.join(os.getenv('ZENHOME'), 'bin',
            REQUEST.form.get('daemon'))
        # we actually want to block here, so that the page doesn't refresh
        # until the action has completed
        log.info("Processing a '%s' for '%s' through the web..." % (action, daemon))
        os.system("%s %s" % (daemon, action))
    security.declareProtected('Manage DMD','manage_daemonAction')
        

InitializeClass(ZenossInfo)
