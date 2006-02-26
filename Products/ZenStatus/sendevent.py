import xmlrpclib
from AuthTransport import BasicAuthTransport

trans = BasicAuthTransport('edahl', 'edahl')
server = xmlrpclib.Server('http://emi0:8080/cvportal/netcool', transport=trans)
e = {}
e['Node'] = 'conrad.confmon.loc'
e['Summary'] = 'this is a test message'
e['Class'] = 100
e['Agent'] = 'PingProbe'
e['Severity'] = 4
e['Type'] = 2
e['AlertGroup'] = 'Ping'
e['NodeAlias'] = '1.2.3.4'

server.sendEvent(e)
