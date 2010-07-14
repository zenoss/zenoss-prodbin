###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging
from Products.ZenUtils.Ext import DirectRouter, DirectResponse
from Products.Zuul.decorators import require
from Products.Zuul.interfaces import ITreeNode
from Products.ZenUtils.jsonutils import unjson
from Products import Zuul

log = logging.getLogger('zen.NetworkRouter')

class NetworkRouter(DirectRouter):
    def __init__(self, context, request):
        super(NetworkRouter, self).__init__(context, request)
        self.api = Zuul.getFacade('network')

    @require('Manage DMD')
    def discoverDevices(self, uid):
        jobStatus = self.api.discoverDevices(uid)
        if jobStatus:
            return DirectResponse.succeed(jobId=jobStatus.id)
        else:
            return DirectResponse.fail()

    @require('Manage DMD')
    def addNode(self, newSubnet, contextUid):
        
        # If the user doesn't include a mask, reject the request.
        if '/' not in newSubnet:
            response = DirectResponse.fail('You must include a subnet mask.')
        else:
            try:
                netip, netmask = newSubnet.split('/')
                netmask = int(netmask)
                foundSubnet = self.api.findSubnet(netip, netmask, '/zport/dmd/Networks')
                
                if foundSubnet is not None:
                    response = DirectResponse.fail('Did not add duplicate subnet: %s (%s/%s)' %
                                                   (newSubnet, foundSubnet.id, foundSubnet.netmask))
                else:
                    newNet = self.api.addSubnet(newSubnet, contextUid)
                    node = ITreeNode(newNet)
                    response = DirectResponse.succeed(newNode=Zuul.marshal(node))

            except Exception as error:
                log.exception(error)
                response = DirectResponse.fail('Error adding subnet: %s (%s)' % (newSubnet, error))

        return response

    @require('Manage DMD')
    def deleteNode(self, uid):
        self.api.deleteSubnet(uid)
        return DirectResponse.succeed(tree=self.getTree())

    def getTree(self, id='/zport/dmd/Networks'):
        tree = self.api.getTree(id)
        data = Zuul.marshal(tree)
        return [data]

    def getInfo(self, uid, keys=None):
        network = self.api.getInfo(uid)
        data = Zuul.marshal(network, keys)
        disabled = not Zuul.checkPermission('Manage DMD')
        return DirectResponse.succeed(data=data, disabled=disabled)

    @require('Manage DMD')
    def setInfo(self, **data):
        network = self.api.getInfo(data['uid'])
        Zuul.unmarshal(data, network)
        return DirectResponse.succeed()

    def getIpAddresses(self, uid, start=0, params=None, limit=50, sort='name',
                   order='ASC'):
        if isinstance(params, basestring):
            params = unjson(params)
        instances = self.api.getIpAddresses(uid=uid, start=start, params=params,
                                          limit=limit, sort=sort, dir=order)

        keys = ['name', 'device', 'interface', 'pingstatus', 'snmpstatus', 'uid']
        data = Zuul.marshal(instances, keys)
        return DirectResponse.succeed(data=data, totalCount=instances.total)
