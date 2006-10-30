"""
Zenoss versioning module.

"""
import os
import re
import sys

__revision__ = int('$Revision$'.split()[-2])

def getVersionTupleFromString(versionString):
    """
    A utility function for parsing dot-delimited stings as a version tuple.

    # test some simple version formats
    >>> version = '1'
    >>> getVersionTupleFromString(version)
    (1, 0, 0)
    >>> version = '1.0'
    >>> getVersionTupleFromString(version)
    (1, 0, 0)
    >>> version = '1.0.0'
    >>> getVersionTupleFromString(version)
    (1, 0, 0)
    >>> version = '1.0.2'
    >>> getVersionTupleFromString(version)
    (1, 0, 2)

    # here's one for Fedora
    >>> version = '2.6.17-1.2174_FC5'
    >>> getVersionTupleFromString(version)
    (2, 6, 17)

    # here's a bizzare one
    >>> version = '1a.23zzX.abs'
    >>> getVersionTupleFromString(version)
    (1, 23, 0)

    # checks against ints and floats being passed instead of strings
    >>> version = 1
    >>> getVersionTupleFromString(version)
    (1, 0, 0)
    >>> version = 1.0
    >>> getVersionTupleFromString(version)
    (1, 0, 0)
    >>> version = 0
    >>> getVersionTupleFromString(version)
    (0, 0, 0)
    """
    versionString = str(versionString)
    versions = re.split('[^0-9]+', versionString.strip())[:3]
    return (lambda x,y=0,z=0: (int(x),int(y or 0),int(z or 0)))(*versions)

class VersionError(Exception):
    pass

class IncomparableVersions(VersionError):
    pass

class ComponentVersionError(VersionError):
    pass

class VersionNotSupported(VersionError):
    pass

class Version(object):
    """
    A class for obtaining and manipulating version numbers as well as creating
    the necessary version files Zenoss utilizes.

    >>> v1 = Version('Zenoss', 0, 22)
    >>> v2 = Version('Zenoss', 0, 23, 4)
    >>> v3 = Version('Zenoss', 0, 23, 7)
    >>> v4 = Version('Zenoss', 1)
    >>> v5 = Version('Zenoss', 1, 0, 2)
    >>> v6 = Version('Zenoss', 1, 0, 2)
    >>> v7 = Version('Zenoss', 1, 0, 2, 15729)
    >>> v8 = Version('Zenoss', 1, 0, 2, 15730)
    >>> v9 = Version('Zenoss', 1, 0, 3, 15729)

    # test the display methods
    >>> v9.short()
    '1.0.3'
    >>> v9.long()
    'Zenoss 1.0.3'
    >>> v9.full()
    'Zenoss 1.0.3 r15729'
    >>> v2.tuple()
    (0, 23, 4)

    # comparisons
    >>> v1 > v2
    False
    >>> v3 > v2
    True
    >>> v4 < v3
    False
    >>> v4 > v5
    False
    >>> v6 > v5
    False
    >>> v6 >= v5
    True
    >>> v6 == v5
    True

    # comparison, one with a revision number
    >>> v7 > v6
    False

    # revision number comparisons
    >>> v7 > v8
    False
    >>> v8 > v9
    False

    # comparing non-Version objects with Version objects
    >>> '1.0.4' > v5
    True
    >>> (1,0,1) > v5
    False
    >>> 1 == v4
    True
    >>> v4 == 1.0
    True
    >>> '1.0' == v4
    True

    # comment/additional info
    >>> v10 = v9
    >>> v10.setComment('A super-secret squirrel release')
    >>> v10.full()
    'Zenoss 1.0.3 r15729 (A super-secret squirrel release)'
    """
    def __init__(self, name, major=0, minor=0, micro=0, revision=0,
        comment=''):
        self.name = name
        self.major = major
        self.minor = minor
        self.micro = micro
        self.revision = revision
        self.comment = str(comment)

    def short(self):
        """
        Returns a string of just the version number.
        """
        return '%d.%d.%d' % (self.major, self.minor, self.micro)

    def long(self):
        """
        Returns a string with the software name and the version.
        """
        return "%s %s" % (self.name, self.short())

    def full(self):
        """
        Returns a string with the software name, the version number, and the
        subversion revision number, if defined.
        """
        comment = ''
        if self.comment:
            comment = ' (' + self.comment + ')'
        return "%s%s%s" % (self.long(), self._formatSVNRevision(), comment)

    def tuple(self):
        """
        Return a version tuple.
        """
        return (self.major, self.minor, self.micro)

    def incrMajor(self):
        self.major += 1

    def incrMinor(self):
        self.minor += 1

    def incrMicro(self):
        self.micro += 1

    def setComment(self, comment):
        self.comment = comment

    def __cmp__(self, other):
        """
        Comparse one verion to another. If the other version supplied is not a
        Version instance, attempt coercion.

        The assumption here is that any non-Version object being compared to a
        Version object represents a verion of the same product with the same
        name but a different version number.
        """
        if other is None:
            return 1
        if isinstance(other, tuple):
            version = '.'.join([ str(x) for x in other ])
            other = Version.parse("%s %s" % (self.name, version))
        elif True in [ isinstance(other, x) for x in [str, int, float, long] ]:
            other = Version.parse("%s %s" % (self.name, str(other)))
        if self.name != other.name:
            raise IncomparableVersions()
        return cmp(self.tuple(), other.tuple())

    def _formatSVNRevision(self):
        svnrev = self.revision
        if svnrev:
            svnrev = ' r%s' % svnrev
        else:
            svnrev = ''
        return svnrev

    def getSVNRevision(self):
        if self.revision:
            return self.revision
        self.revision = getZenossRevision()
        return self.revision

    def __repr__(self):
        return '%s(%s, %d, %d, %d,%s)' % (
            self.__class__.__name__,
            self.name,
            self.major,
            self.minor,
            self.micro,
            self._formatSVNRevision())

    def __str__(self):
        return '[%s, version %d.%d.%d%s]' % (
            self.name,
            self.major,
            self.minor,
            self.micro,
            self._formatSVNRevision())

    def parse(self, versionString):
        """
        Parse the version info from a string. This method is usable without
        having instantiated Version, and returns an instantiation.

        The expected form is the following:
            software_name W.X.Y rZ
        where W, X, and Y represent the major, minor, and micro version numbers
        and Z is the subversion revision number.

        Only the software name is required.

        The version number is expected to have at least a major version number.
        Minor and micro version numbers are optional, but if they are provided,
        they must be dot-delimited.

        Here are some example usages:

        >>> v = Version.parse('Zenoss')
        >>> repr(v)
        'Version(Zenoss, 0, 0, 0,)'
        >>> print v
        [Zenoss, version 0.0.0]

        >>> v = Version.parse('Zenoss 1')
        >>> repr(v)
        'Version(Zenoss, 1, 0, 0,)'
        >>> print v
        [Zenoss, version 1.0.0]

        >>> v = Version.parse('Zenoss 0.26.4')
        >>> repr(v)
        'Version(Zenoss, 0, 26, 4,)'
        >>> print v
        [Zenoss, version 0.26.4]


        >>> v = Version.parse('Zenoss 0.32.1 r13667')
        >>> repr(v)
        'Version(Zenoss, 0, 32, 1, r13667)'
        >>> print v
        [Zenoss, version 0.32.1 r13667]
        """
        versionParts = versionString.strip().split()
        name = versionParts.pop(0)
        #raise str(versionParts)
        try:
            # we want to always have a tuple of the right size returned,
            # regardless of the number of elements in ther 'versions' iterable
            major, minor, micro = getVersionTupleFromString(
                versionParts.pop(0))
            try:
                revision = versionParts.pop(0).strip('r')
            except IndexError:
                revision = ''
        except IndexError:
            major = minor = micro = 0
            revision = ''
        self = Version(name, major, minor, micro, revision)
        return self
    parse = classmethod(parse)

def getOSVersion():
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
    return (name, major, minor, micro, 0, comment)

def getPythonVersion():
    """
    This function returns a Version-ready tuple. For use with the Version
    object, use exteneded call syntax:

        v = Version(*getPythonVersion())
        v.full()
    """
    name = 'Python'
    major, minor, micro, releaselevel, serial = sys.version_info
    return (name, major, minor, micro)

def getMySQLVersion():
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
    return (name, major, minor, micro, 0, comment)

def getRRDToolVersion():
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
    return (name, major, minor, micro)

def getTwistedVersion():
    """
    This function returns a Version-ready tuple. For use with the Version
    object, use exteneded call syntax:

        v = Version(*getTwistedVersion())
        v.full()
    """
    from twisted._version import version as v

    return ('Twisted', v.major, v.minor, v.micro)

def getPySNMPVersion():
    """
    This function returns a Version-ready tuple. For use with the Version
    object, use exteneded call syntax:

        v = Version(*getpySNMPVersion())
        v.full()
    """
    from pysnmp.version import getVersion

    return ('PySNMP',) + getVersion()

def getTwistedSNMPVersion():
    """
    This function returns a Version-ready tuple. For use with the Version
    object, use exteneded call syntax:

        v = Version(*getTwistedSNMPVersion())
        v.full()
    """
    from twistedsnmp.version import version

    return ('TwistedSNMP',) + version
    
def getZopeVersion():
    """
    This function returns a Version-ready tuple. For use with the Version
    object, use exteneded call syntax:

        v = Version(*getZopeVersion())
        v.full()
    """
    from App import version_txt as version

    name = 'Zope'
    major, minor, micro, status, release = version.getZopeVersion()
    return (name, major, minor, micro)

def getZenossVersion(component='None'):
    """
    A convenience function for obtianing the current version of Zenoss and
    Zenoss components.
    """
    # right now, this function is not used, as the Zenoss version is updated
    # dynamically by zenpkg.
    pass

def getZenossRevision():
    return __revision__
    
def createCurrentVersionModule(major=0, minor=0, micro=0, version=''):
    """
    This method creates/overwrites Products.ZenMode.version.Current with
    the version information stored in this Version() object.
    """
    moduleString = """# This file is generated automatically during packaging and installation.
# ALL CHANGES TO THIS FILE WILL BE OVERWRITTEN!!!
# For permanent changes, please edit Version.py.

import Globals
from Products.ZenUtils.Version import *

# OS and Software Dependencies
os = Version(*getOSVersion())
python = Version(*getPythonVersion())
mysql = Version(*getMySQLVersion())
rrdtool = Version(*getRRDToolVersion())
twisted = Version(*getTwistedVersion())
pysnmp = Version(*getPySNMPVersion())
twistedsnmp = Version(*getTwistedSNMPVersion())
zope = Version(*getZopeVersion())

# Zenoss components
zenmodel = Version('Zenoss', %s, getZenossRevision())
zenoss = zenmodel
version = zenoss.full()

# Utility function for display
def getVersions():
    vers = {
        'OS': os.full(),
        'Python': python.full(),
        'Database': mysql.full(),
        'RRD': rrdtool.full(),
        'Twisted': twisted.full(),
        'SNMP': pysnmp.full() + ', ' + twistedsnmp.full(),
        'Zope': zope.full(),
        'Zenoss': zenoss.full(),
    }
    return vers

if __name__ == '__main__':
    for v in getVersions():
        print v
    """
    if version:
        major, minor, micro = getVersionTupleFromString(version)
    else:
        version = "%d, %d, %d" % (major, minor, micro)
    vers = Version('Zenoss', major, minor, micro)
    #revision = vers.getSVNRevision()
    #if revision:
    #    version += ", %s" % revision
    dstFile = os.path.join(os.getenv('ZENHOME'), 'Products', 'ZenModel',
        'version', 'Current.py')
    fh = open(dstFile, 'w+')
    fh.write(moduleString % version)
    fh.close()
    return dstFile

def _test():
    import doctest
    doctest.testmod()

if __name__ == '__main__':
    _test()
