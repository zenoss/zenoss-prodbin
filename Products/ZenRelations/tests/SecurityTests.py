#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

import xmlrpclib

testbase = 'http://localhost:8080/rmtest'

def runTests():
    server = xmlrpclib.Server(testbase)
    try:
        server.manage_workspace()
        raise "Test Failed"
    except xmlrpclib.Fault, e:
        if not e.faultString.find('not authorized'):
            raise "Test Failed"
    try:
        server.manage_afterAdd()
        raise "Test Failed"
    except xmlrpclib.Fault, e:
        if not e.faultString.find('not authorized'):
            raise "Test Failed"
    print "Tests OK"
    

if __name__ == '__main__':
    runTests()
