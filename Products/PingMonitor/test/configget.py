import xmlrpclib
from AuthTransport import BasicAuthTransport

username='edahl'
password='sine440'
pingconfsrv='http://localhost:8080/zport/dmd/Monitors/StatusMonitors/Default'

trans = BasicAuthTransport(username, password)
server = xmlrpclib.Server(pingconfsrv,transport=trans)
devices = server.getPingDevices()
for device in devices:
    print device
