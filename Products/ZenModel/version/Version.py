"""
Zenoss versioning module.

XXX
Note that when ZenCore or ZenBase is abstracted out, this should be moved as
well.
"""
class VersionError(Exception):
    pass

class IncomparableVersions(VersionError):
    pass

class ComponentVersionError(VersionError):
    pass

class Version(object):
    """
    A class for obtaining and manipulating version numbers as well as creating
    the necessary version files Zenoss utilizes.
    """
    def __init__(self, name, major, minor, micro):
        self.name = name
        self.major = major
        self.minor = minor
        self.micro = micro
        self.revision = ''

    def _getSVNVersion13(self):
        """
        For all versions of Subversion that support XML .svn/entries files.
        """
        pass

    def _getSVNVersion14(self):
        """
        As of version 1.4 of Subversion, XML .svn/entries failes are no longer
        supported. This method is for extracting revision information from SVN
        1.4+.
        """
        pass

    def getSVNVersion(self):
        try:
            v = self._getSVNVersion13()
        except ComponentVersionError:
            v = self._getSVNVersion14()
        self.revision = v
        return self.revision

    def createCurrentVersionModule(self):
        """
        This method creates/overwrites Products.ZenMode.version.Current with
        the version information stored in this Version() object.
        """

def getOSVersion():
    pass

def getPythonVersion():
    pass

def getMySQLVersion():
    pass

def getRRDToolVersion():
    pass

def getTwistedVersion():
    pass

def getpySNMPVersion():
    pass

def getTwistedSNMPVersion():
    pass

def getZopeVersion():
    pass

def getZenossVersion(component='ZenModel'):
    """
    A convenience function for obtianing the current version of Zenoss and
    Zenoss components.
    """
    try:
        pass
    except ImportError:
        # try to get version from VERSION.txt
        # instantiate Version and try to get svn version
        pass

def getCurrentVersions():
    """
    This function returns a dictionary whose keys are software component names
    and whose values are Version objects. This is the public function that
    should be accessed for all component software.
    """
    pass
