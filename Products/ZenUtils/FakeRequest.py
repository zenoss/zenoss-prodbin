###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################


class FakeRequest(dict):
    ''' Used for ajax calls from event console and elsewhere.  This is used
    as a container for REQUEST['message'] which we are interested in.  It has
    the advantage over the regular REQUEST object in that it won't actually
    bother to render anything when callZenScreen() is called with one.
    '''
    dontRender = True
    dontRedirect = True
    
    def __init__(self, *args, **kw):
        dict.__init__(self, *args, **kw)
        self['oneKeyValueSoInstanceIsntEmptyAndEvalToFalse'] = True
        
    def setMessage(self, R):
        if R and self.get('message', ''):
            R['message'] = self['message']

