from Version import *

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
zenmodel = Version('Zenoss', 0, 23, 1)
zenoss = zenmodel
version = zenoss.full()

# Utility function for display
def getVersions():
    vers = []
    for v in [os, python, zope, mysql, rrdtool, twisted, pysnmp, twistedsnmp,
        zenoss]:
        vers.append(v.full())
    return vers

if __name__ == '__main__':
    for v in getVersions():
        print v
