#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''RRDService

Provides RRD services to zenhub clients.
'''

from HubService import HubService

class RRDService(HubService):


    def __init__(self, dmd, instance = None):
        HubService.__init__(self, dmd, instance)


    def remote_writeRRD(self, *args, **kw):
        pass
