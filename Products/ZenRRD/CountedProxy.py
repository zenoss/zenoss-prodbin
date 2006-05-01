#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

CountedProxy: track outstanding xmlrpc requests.

$Id$
'''

__version__ = "$Revision$"[11:-2]

_callback = None

_count = 0
class CountedProxy:
    "count the number of outstanding xmlrpc requests"
    def __init__(self, proxy):
        self.proxy = proxy

    def finished(self, arg):
        "decrease counter and chain to the next callback"
        global _count
        _count -= 1
        if _count == 0 and _callback:
            _callback()
        return arg

    def callRemote(self, method, *args):
        "increase counter and chain to our callback"
        global _count
        d = self.proxy.callRemote(method, *args)
        _count += 1
        d.addBoth(self.finished)
        return d

def setCallback(cback):
    "call someone when the count goes to zero"
    global _callback
    _callback = cback

def allFinished():
    "check for oustanding requests"
    return _count == 0

