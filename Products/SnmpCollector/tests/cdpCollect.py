from Products.SnmpCollector.SnmpSession import SnmpSession
import sys

s = SnmpSession(sys.argv[1], community='subaru')

cdpoid='.1.3.6.1.4.1.9.9.23.1.2.1.1'
cdpmap={
        '.3': 'addressType',
        '.4': 'rAddress',
        '.6':'rDevice', 
        '.7': 'rInterfaceName',
        '.11':'vlan', 
       }

data=s.collectSnmpTableMap(cdpoid, cdpmap)

for k,v in data.items():
    if v.has_key('rAddress'): 
        print s.asip(v['rAddress']),
    print v['rDevice'], v['rInterfaceName']
	#print v
