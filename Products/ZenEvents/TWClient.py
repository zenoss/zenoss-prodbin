import SOAPpy
server = SOAPpy.SOAPProxy("http://localhost:7080/")
print server.hello()
