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
    Traceback (most recent call last):
    IncomparableVersions

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
    """
    def __init__(self, name, major=0, minor=0, micro=0, revision=0):
        self.name = name
        self.major = major
        self.minor = minor
        self.micro = micro
        self.revision = revision

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
        return "%s%s" % (self.long(), self._formatSVNRevision())

    def __cmp__(self, other):
        """
        Comparse one verion to another. If the other version supplied is not a
        Version instance, attempt coercion.

        The assumption here is that any non-Version object being compared to a
        Version object represents a verion of the same product with the same
        name but a different version number.
        """
        if isinstance(other, tuple):
            version = '.'.join([ str(x) for x in other ])
            other = Version.parse("%s %s" % (self.name, version))
        elif True in [ isinstance(other, x) for x in [str, int, float, long] ]:
            other = Version.parse("%s %s" % (self.name, str(other)))
        if self.name != other.name:
            raise IncomparableVersions()
        if not self.revision:
            if other.revision:
                raise IncomparableVersions()
            comparison = cmp(
                (self.major, self.minor, self.micro),
                (other.major, other.minor, other.micro))
        else:
            if not other.revision:
                raise IncomparableVersions()
            comparison = cmp(
                (self.major, self.minor, self.micro, self.revision),
                (other.major, other.minor, other.micro, other.revision))
        return comparison

    def _getSVNVersion13(self):
        """
        For all versions of Subversion that support XML .svn/entries files.
        """
        return ''

    def _getSVNVersion14(self):
        """
        As of version 1.4 of Subversion, XML .svn/entries failes are no longer
        supported. This method is for extracting revision information from SVN
        1.4+.
        """
        return ''

    def _formatSVNRevision(self):
        svnrev = self.revision
        if svnrev:
            svnrev = ' r%s' % svnrev
        return svnrev

    def getSVNVersion(self):
        if self.revision:
            return self.revision
        try:
            v = self._getSVNVersion13()
        except ComponentVersionError:
            v = self._getSVNVersion14()
        self.revision = v
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

    def createCurrentVersionModule(self):
        """
        This method creates/overwrites Products.ZenMode.version.Current with
        the version information stored in this Version() object.
        """

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
            versions = versionParts.pop(0).split('.')
            # we want to always have a tuple of the right size returned,
            # regardless of the number of elements in versions
            (major, minor, micro) = (lambda x,y=0,z=0:
                (int(x),int(y),int(z)))(*versions)
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

def _test():
    import doctest
    doctest.testmod()

if __name__ == '__main__':
    _test()
