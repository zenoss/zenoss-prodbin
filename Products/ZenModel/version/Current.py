# This file is generated automatically during packaging and installation.
# ALL CHANGES TO THIS FILE WILL BE OVERWRITTEN!!!
# For permanent changes, please edit Version.py.

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
zenmodel = Version('Zenoss', 0, 0, 0)
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
        'SNMP': pysnmp.full() + ', ' + twistedsnmp.full()), 
        'Zope': zope.full(), 
        'Zenoss': zenoss.full(), 
    } 
    return vers

if __name__ == '__main__':
    for v in getVersions():
        print v
    