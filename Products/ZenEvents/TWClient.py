import SOAPpy
import xmlrpclib
sserver = SOAPpy.SOAPProxy("http://localhost:7080/SOAP")
xserver = xmlrpclib.ServerProxy("http://localhost:7080/XMLRPC")
