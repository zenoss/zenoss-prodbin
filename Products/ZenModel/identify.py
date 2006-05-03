#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""identify

identify what type a device is

$Id: identify.py,v 1.1 2002/09/17 19:47:32 edahl Exp $"""

__version__ = "$Revision: 1.1 $"[11:-2]

from Products.SnmpCollector import SnmpSession
import sys

if __name__ == '__main__':
    filename = sys.argv[1]
    community = sys.argv[2]
    if len(sys.argv) > 3:
        port = sys.argv[3] or 161
    lines = open(filename).readlines()
    lineNumber = 0
    for line in lines:
        lineNumber += 1
        dev = line.strip()
        sess = SnmpSession(dev, community, timeout=1, retries=1)
        print "device", dev,
        try:
            print "descr =", sess.get('.1.3.6.1.2.1.1.1.0').values()[0]
        except:
            print "problem with device", dev
