
from AuthTransport import BasicAuthTransport
import xmlrpclib

username = 'edahl'
password = 'sine440'
url = 'localhost:8080/RrdRenderServer'

trans = BasicAuthTransport(username, password)
server = xmlrpclib.Server(url,transport=trans)

i = server.render
