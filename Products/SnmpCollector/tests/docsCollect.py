from Products.SnmpCollector.SnmpSession import SnmpSession
import sys

s = SnmpSession(sys.argv[1], community='subaru')

cdpoid='.1.3.6.1.2.1.10.127.1.3.3.1'
cdpmap={
        '.2': 'cmMacAddress',
        '.3': 'cmIpAddress',
        '.4':'downstreamIfIndex', 
        '.5': 'upstreamIfIndex',
       }

data=s.collectSnmpTableMap(cdpoid, cdpmap, bulk=1)

for k,v in data.items():
	print v
