import os
import re
import time
import logging
log = logging.getLogger("zen.ZenossInfo")

from Globals import InitializeClass
from OFS.SimpleItem import SimpleItem
from AccessControl import ClassSecurityInfo

from Products.ZenModel.ZenModelItem import ZenModelItem
from Products.ZenUtils import Time
from Products.ZenUtils.Version import *

from Products.ZenEvents.UpdateCheck import UpdateCheck, parseVersion

def manage_addZenossInfo(context, id='About', REQUEST=None):
    """
    Provide an instance of ZenossInfo for the portal.
    """
    about = ZenossInfo(id)
    context._setObject(id, about)
    if REQUEST is not None:
        REQUEST.RESPONSE.redirect(context.absolute_url() +'/manage_main')

class ZenossInfo(ZenModelItem, SimpleItem):

    portal_type = meta_type = 'ZenossInfo'

    security = ClassSecurityInfo()

    _properties = (
        {'id':'id', 'type':'string'},
        {'id':'title', 'type':'string'},
    )

    factory_type_information = ( 
        { 
            'immediate_view' : 'zenossInfo',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'zenossInfo'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'versions'
                , 'name'          : 'Versions'
                , 'action'        : 'zenossVersions'
                , 'permissions'   : ( "Manage DMD", )
                },
           )
          },
        ) 

    security.declarePublic('getZenossVersion')
    def getZenossVersion(self):
        from Products.ZenModel.ZVersion import VERSION
        return Version.parse("Zenoss %s %s" % 
                    (VERSION, self.getZenossRevision()))

    security.declarePublic('getZenossVersionShort')
    def getZenossVersionShort(self):
        return self.getZenossVersion().short()

    def getOSVersion(self):
        """
        This function returns a Version-ready tuple. For use with the Version
        object, use exteneded call syntax:

            v = Version(*getOSVersion())
            v.full()
        """
        if os.name == 'posix':
            sysname, nodename, version, build, arch = os.uname()
            name = "%s (%s)" % (sysname, arch)
            major, minor, micro = getVersionTupleFromString(version)
            comment = ' '.join(os.uname())
        elif os.name == 'nt':
            from win32api import GetVersionEx
            major, minor, micro, platformID, additional = GetVersionEx()
            name = 'Windows %s (%s)' % (os.name.upper(), additional)
            comment = ''
        else:
            raise VersionNotSupported
        return Version(name, major, minor, micro, 0, comment)

    def getPythonVersion(self):
        """
        This function returns a Version-ready tuple. For use with the Version
        object, use exteneded call syntax:

            v = Version(*getPythonVersion())
            v.full()
        """
        name = 'Python'
        major, minor, micro, releaselevel, serial = sys.version_info
        return Version(name, major, minor, micro)

    def getMySQLVersion(self):
        """
        This function returns a Version-ready tuple. For use with the Version
        object, use exteneded call syntax:

            v = Version(*getMySQLVersion())
            v.full()

        The regex was tested against the following output strings:
            mysql  Ver 14.12 Distrib 5.0.24, for apple-darwin8.5.1 (i686) using readline 5.0
            mysql  Ver 12.22 Distrib 4.0.24, for pc-linux-gnu (i486)
            mysql  Ver 14.12 Distrib 5.0.24a, for Win32 (ia32)
        """
        cmd = 'mysql --version'
        fd = os.popen(cmd)
        output = fd.readlines()
        version = "0"
        if fd.close() is None and len(output) > 0:
            output = output[0].strip()
            regexString = '(mysql).*Ver [0-9]{2}\.[0-9]{2} '
            regexString += 'Distrib ([0-9]+.[0-9]+.[0-9]+)(.*), for (.*\(.*\))'
            regex = re.match(regexString, output)
            if regex:
                name, version, release, info = regex.groups()
        comment = 'Ver %s' % version
        # the name returned in the output is all lower case, so we'll make our own
        name = 'MySQL'
        major, minor, micro = getVersionTupleFromString(version)
        return Version(name, major, minor, micro, 0, comment)

    def getRRDToolVersion(self):
        """
        This function returns a Version-ready tuple. For use with the Version
        object, use exteneded call syntax:

            v = Version(*getRRDToolVersion())
            v.full()
        """
        cmd = os.path.join(os.getenv('ZENHOME'), 'bin', 'rrdtool')
        if not os.path.exists(cmd):
            cmd = 'rrdtool'
        fd = os.popen(cmd)
        output = fd.readlines()[0].strip()
        fd.close()
        name, version = output.split()[:2]
        major, minor, micro = getVersionTupleFromString(version)
        return Version(name, major, minor, micro)

    def getTwistedVersion(self):
        """
        This function returns a Version-ready tuple. For use with the Version
        object, use exteneded call syntax:

            v = Version(*getTwistedVersion())
            v.full()
        """
        from twisted._version import version as v

        return Version('Twisted', v.major, v.minor, v.micro)

    def getPySNMPVersion(self):
        """
        This function returns a Version-ready tuple. For use with the Version
        object, use exteneded call syntax:

            v = Version(*getpySNMPVersion())
            v.full()
        """
        from pysnmp.version import getVersion
        return Version('PySNMP', *getVersion())

    def getTwistedSNMPVersion(self):
        """
        This function returns a Version-ready tuple. For use with the Version
        object, use exteneded call syntax:

            v = Version(*getTwistedSNMPVersion())
            v.full()
        """
        from twistedsnmp.version import version
        return Version('TwistedSNMP', *version)
        
    def getZopeVersion(self):
        """
        This function returns a Version-ready tuple. For use with the Version
        object, use exteneded call syntax:

            v = Version(*getZopeVersion())
            v.full()
        """
        from App import version_txt as version

        name = 'Zope'
        major, minor, micro, status, release = version.getZopeVersion()
        return Version(name, major, minor, micro)

    
    def getZenossRevision(self):
        try:
            os.chdir(os.path.join(os.getenv('ZENHOME'), 'Products'))
            fd = os.popen("svn info | grep Revision | awk '{print $2}'")
            return fd.readlines()[0].strip()
        except:
            return ''


    def getAllVersions(self):
        """
        Return a list of version numbers for currently tracked component
        software.
        """
        versions = (
        {'header': 'Zenoss', 'data': self.getZenossVersion().full()},
        {'header': 'OS', 'data': self.getOSVersion().full()},
        {'header': 'Zope', 'data': self.getZopeVersion().full()},
        {'header': 'Python', 'data': self.getPythonVersion().full()},
        {'header': 'Database', 'data': self.getMySQLVersion().full()},
        {'header': 'RRD', 'data': self.getRRDToolVersion().full()},
        {'header': 'Twisted', 'data': self.getTwistedVersion().full()},
        {'header': 'SNMP', 'data': self.getPySNMPVersion().full()},
        {'header': 'Twisted SNMP', 'data': self.getTwistedSNMPVersion().full()},
        )
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

    def _pidRunning(self, pid):
        try:
            os.kill(pid, 0)
            return pid
        except OSError, ex:
            import errno
            errnum, msg = ex.args
            if errnum == errno.EPERM:
                return pid

    def _getDaemonPID(self, name):
        """
        For a given daemon name, return its PID from a .pid file.
        """
        if name == 'zopectl':
            name = 'Z2'
        elif name == 'zeoctl':
            name = 'ZEO'
        else:
            name = "%s.py" % name
        pidFile = os.path.join(os.getenv('ZENHOME'), 'var', '%s.pid' % name)
        if os.path.exists(pidFile):
            pid = open(pidFile).read()
            try:
                pid = int(pid)
            except ValueError:
                return None
            return self._pidRunning(int(pid))
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

    def manage_daemonAction(self, REQUEST):
        """
        Start, stop, or restart Zenoss daemons from a web interface.
        """
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
        if action == 'stop': time.sleep(2)
        return self.callZenScreen(REQUEST)
    security.declareProtected('Manage DMD','manage_daemonAction')

    def manage_checkVersion(self, optInOut=False, optInOutMetrics=False, REQUEST=None):
        "Check for Zenoss updates on the Zenoss website"
        self.dmd.versionCheckOptIn = optInOut
        self.dmd.reportMetricsOptIn = optInOutMetrics
        # There is a hidden field for manage_checkVersions in the form so that
        # the javascript submit() calls will end up calling this method.
        # That means that when user hits the Check Now button we will receive
        # 2 values for that field.  (button is that same field name.)
        # We want to initiate only when the button is pressed.
        if self.dmd.versionCheckOptIn \
          and REQUEST \
          and isinstance(REQUEST.form['manage_checkVersion'], list):
            uc = UpdateCheck()
            uc.check(self.dmd, self.dmd.ZenEventManager, manual=True)
        return self.callZenScreen(REQUEST)
    security.declareProtected('Manage DMD','manage_checkVersion')

    def lastVersionCheckedString(self):
        if not self.dmd.lastVersionCheck:
            return "Never"
        return Time.LocalDateTime(self.dmd.lastVersionCheck)

    def versionBehind(self):
        if self.dmd.availableVersion is None:
            return False
        import pdb; pdb.set_trace()
        if parseVersion(self.dmd.availableVersion) > self.getZenossVersion():
            return True
        return False

    
InitializeClass(ZenossInfo)
