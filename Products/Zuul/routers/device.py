###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
"""
Operations for Device Organizers and Devices.

Available at:  /zport/dmd/device_router
"""

import logging
from itertools import islice
from AccessControl import Unauthorized
from Products.ZenUtils.Ext import DirectResponse
from Products.ZenUtils.jsonutils import unjson
from Products import Zuul
from Products.Zuul.routers import TreeRouter
from Products.Zuul.form.interfaces import IFormBuilder
from Products.Zuul.decorators import require
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier

log = logging.getLogger('zen.Zuul')


class DeviceRouter(TreeRouter):
    """
    A JSON/ExtDirect interface to operations on devices
    """

    @require('Manage DMD')
    def addLocationNode(self, type, contextUid, id,
                        description=None, address=None):
        """
        Adds a new location organizer specified by the parameter id to
        the parent organizer specified by contextUid.

        contextUid must be a path to a Location.

        @type  type: string
        @param type: Node type (always 'organizer' in this case)
        @type  contextUid: string
        @param contextUid: Path to the location organizer that will
               be the new node's parent (ex. /zport/dmd/Devices/Locations)
        @type  id: string
        @param id: The identifier of the new node
        @type  description: string
        @param description: (optional) Describes the new location
        @type  address: string
        @param address: (optional) Physical address of the new location
        @rtype:   dictionary
        @return:  B{Properties}:
           - success: (bool) Success of node creation
           - nodeConfig: (dictionary) The new location's properties
        """
        result = {}
        try:
            facade = self._getFacade()
            organizer = facade.addLocationOrganizer(contextUid,
                                                    id,
                                                    description,
                                                    address)
            uid = organizer.uid

            treeNode = facade.getTree(uid)
            result['nodeConfig'] = Zuul.marshal(treeNode)
            result['success'] = True
        except Exception, e:
            log.exception(e)
            result['msg'] = str(e)
            result['success'] = False
        return result

    def _getFacade(self):
        return Zuul.getFacade('device', self.context)

    def getTree(self, id):
        """
        Returns the tree structure of an organizer hierarchy where
        the root node is the organizer identified by the id parameter.

        @type  id: string
        @param id: Id of the root node of the tree to be returned
        @rtype:   [dictionary]
        @return:  Object representing the tree
        """
        facade = self._getFacade()
        tree = facade.getTree(id)
        data = Zuul.marshal(tree)
        return [data]

    def getComponents(self, uid=None, meta_type=None,
                      keys=None, start=0, limit=50,
                      sort='name', dir='ASC', name=None):
        """
        Retrieves all of the components at a given UID. This method
        allows for pagination.

        @type  uid: string
        @param uid: Unique identifier of the device whose components are
                    being retrieved
        @type  meta_type: string
        @param meta_type: (optional) The meta type of the components to be
                          retrieved (default: None)
        @type  keys: list
        @param keys: (optional) List of keys to include in the returned
                     dictionary. If None then all keys will be returned
                     (default: None)
        @type  start: integer
        @param start: (optional) Offset to return the results from; used in
                      pagination (default: 0)
        @type  limit: integer
        @param limit: (optional) Number of items to return; used in pagination
                      (default: 50)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return results;
                     (default: 'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @type  name: regex
        @param name: (optional) Used to filter the results (default: None)
        @rtype:   DirectResponse
        @return:  B{Properties}:
           - data: (dictionary) The components returned
           - totalCount: (integer) Number of items returned
           - hash: (string) Hashcheck of the current component state (to check
           whether components have changed since last query)
        """
        facade = self._getFacade()
        comps = facade.getComponents(uid, meta_type=meta_type, start=start,
                                     limit=limit, sort=sort, dir=dir,
                                     name=name)
        data = Zuul.marshal(comps, keys=keys)
        return DirectResponse(data=data, totalCount=comps.total,
                              hash=comps.hash_)

    def getComponentTree(self, uid=None, id=None):
        """
        Retrieves all of the components set up to be used in a
        tree.

        @type  uid: string
        @param uid: Unique identifier of the root of the tree to retrieve
        @type  id: string
        @param id: not used
        @rtype:   [dictionary]
        @return:  Component properties in tree form
        """
        if id:
            uid = id
        facade = self._getFacade()
        data = facade.getComponentTree(uid)
        sevs = [c[0].lower() for c in
                self.context.ZenEventManager.severityConversions]
        data.sort(cmp=lambda a, b: cmp(sevs.index(a['severity']),
                                     sevs.index(b['severity'])))
        result = []
        for datum in data:
            result.append(dict(
                id=datum['type'],
                path='Components/%s' % datum['type'],
                text={
                    'text': datum['type'],
                    'count': datum['count'],
                    'description': 'components'},
                iconCls='tree-severity-icon-small-' + datum['severity'],
                leaf=True))
        return result

    def findComponentIndex(self, componentUid, uid=None, meta_type=None,
                           sort='name', dir='ASC', name=None, **kwargs):
        """
        Given a component uid and the component search criteria, this retrieves
        the position of the component in the results.

        @type  componentUid: string
        @param componentUid: Unique identifier of the component whose index
                             to return
        @type  uid: string
        @param uid: Unique identifier of the device queried for components
        @type  meta_type: string
        @param meta_type: (optional) The meta type of the components to retrieve
                          (default: None)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return results (default:
                     'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @type  name: regex
        @param name: (optional) Used to filter the results (default: None)
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - index: (integer) Index of the component
        """
        facade = self._getFacade()
        i = facade.findComponentIndex(componentUid, uid,
                                      meta_type, sort, dir, name)
        return DirectResponse(index=i)

    def getForm(self, uid):
        """
        Given an object identifier, this returns all of the editable fields
        on that object as well as their ExtJs xtype that one would
        use on a client side form.

        @type  uid: string
        @param uid: Unique identifier of an object
        @rtype:   DirectResponse
        @return:  B{Properties}
           - form: (dictionary) form fields for the object
        """
        info = self._getFacade().getInfo(uid)
        form = IFormBuilder(info).render(fieldsets=False)
        form = Zuul.marshal(form)
        return DirectResponse(form=form)

    def getInfo(self, uid, keys=None):
        """
        Get the properties of a device or device organizer

        @type  uid: string
        @param uid: Unique identifier of an object
        @type  keys: list
        @param keys: (optional) List of keys to include in the returned
                     dictionary. If None then all keys will be returned
                     (default: None)
        @rtype:   DirectResponse
        @return:  B{Properties}
            - data: (dictionary) Object properties
            - disabled: (bool) If current user doesn't have permission to use setInfo
        """
        facade = self._getFacade()
        process = facade.getInfo(uid)
        data = Zuul.marshal(process, keys)
        disabled = not Zuul.checkPermission('Manage DMD', self.context)
        return DirectResponse(data=data, disabled=disabled)

    def setInfo(self, **data):
        """
        Set attributes on a device or device organizer.
        This method accepts any keyword argument for the property that you wish
        to set. The only required property is "uid".

        @type    uid: string
        @keyword uid: Unique identifier of an object
        @rtype: DirectResponse
        """
        facade = self._getFacade()
        if not Zuul.checkPermission('Manage DMD', self.context):
            raise Exception('You do not have permission to save changes.')
        process = facade.getInfo(data['uid'])
        Zuul.unmarshal(data, process)
        return DirectResponse()

    @require('Manage Device')
    def setProductInfo(self, uid, **data):
        """
        Sets the ProductInfo on a device. This method has the following valid
        keyword arguments:

        @type    uid: string
        @keyword uid: Unique identifier of a device
        @type    hwManufacturer: string
        @keyword hwManufacturer: Hardware manufacturer
        @type    hwProductName: string
        @keyword hwProductName: Hardware product name
        @type    osManufacturer: string
        @keyword osManufacturer: Operating system manufacturer
        @type    osProductName: string
        @keyword osProductName: Operating system product name
        @rtype:  DirectResponse
        """
        facade = self._getFacade()
        facade.setProductInfo(uid, **data)
        return DirectResponse()

    def getDeviceUuidsByName(self, query=""):
        """
        Retrieves a list of device uuids. For use in combos.
        """
        facade = self._getFacade()
        devices = facade.getDevices(params={'name':query})
        result = []
        for dev in devices:
            result.append({'name':dev.name,
                           'uuid':IGlobalIdentifier(dev._object).getGUID()})
        return DirectResponse.succeed(data=result)


    def getDevices(self, uid=None, start=0, params=None, limit=50, sort='name',
                   dir='ASC'):
        """
        Retrieves a list of devices. This method supports pagination.

        @type  uid: string
        @param uid: Unique identifier of the organizer to get devices from
        @type  start: integer
        @param start: (optional) Offset to return the results from; used in
                      pagination (default: 0)
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       Can be one of the following: name, ipAddress,
                       deviceClass, or productionState (default: None)
        @type  limit: integer
        @param limit: (optional) Number of items to return; used in pagination
                      (default: 50)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return results (default:
                     'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - devices: (list) Dictionaries of device properties
             - totalCount: (integer) Number of devices returned
             - hash: (string) Hashcheck of the current device state (to check
             whether devices have changed since last query)
        """
        facade = self._getFacade()
        if isinstance(params, basestring):
            params = unjson(params)
        devices = facade.getDevices(uid, start, limit, sort, dir, params)
        keys = ['name', 'ipAddress', 'productionState', 'events', 'ipAddressString']
        data = Zuul.marshal(devices, keys)
        return DirectResponse(devices=data, totalCount=devices.total,
                              hash=devices.hash_)

    def moveDevices(self, uids, target, hashcheck, ranges=(), uid=None,
                    params=None, sort='name', dir='ASC'):
        """
        Moves the devices specified by uids to the organizer specified by 'target'.
        
        @type  uids: [string]
        @param uids: List of device uids to move
        @type  target: string
        @param target: Uid of the organizer to move the devices to
        @type  hashcheck: string
        @param hashcheck: Hashcheck for the devices (from getDevices())
        @type  ranges: [integer]
        @param ranges: (optional) List of two integers that are the min/max
                       values of a range of uids to include (default: None)
        @type  uid: string
        @param uid: (optional) Organizer to use when using ranges to get
                    additional uids (default: None)
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       Can be one of the following: name, ipAddress,
                       deviceClass, or productionState (default: None)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return result (default:
                     'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - tree: ([dictionary]) Object representing the new device tree
             - exports: (integer) Number of devices moved
        """
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)

        facade = self._getFacade()
        try:
            exports = facade.moveDevices(uids, target)
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to move devices.')
        else:
            target = '/'.join(target.split('/')[:4])
            tree = self.getTree(target)
            return DirectResponse.succeed(tree=tree, exports=exports)

    @require('Manage Device')
    def pushChanges(self, uids, hashcheck, ranges=(), uid=None, params=None,
                    sort='name', dir='ASC'):
        """
        Push changes on device(s) configuration to collectors.

        @type  uids: [string]
        @param uids: List of device uids to push changes
        @type  hashcheck: string
        @param hashcheck: Hashcheck for the devices (from getDevices())
        @type  ranges: [integer]
        @param ranges: (optional) List of two integers that are the min/max
                       values of a range of uids to include (default: None)
        @type  uid: string
        @param uid: (optional) Organizer to use when using ranges to get
                    additional uids (default: None)
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       Can be one of the following: name, ipAddress,
                       deviceClass, or productionState (default: None)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return result (default:
                     'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @rtype:   DirectResponse
        @return:  Success message
        """
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)

        facade = self._getFacade()
        facade.pushChanges(uids)
        return DirectResponse.succeed('Changes pushed to collectors.')

    @require('Manage Device')
    def lockDevices(self, uids, hashcheck, ranges=(), updates=False,
                    deletion=False, sendEvent=False, uid=None, params=None,
                    sort='name', dir='ASC'):
        """
        Lock device(s) from changes.

        @type  uids: [string]
        @param uids: List of device uids to lock
        @type  hashcheck: string
        @param hashcheck: Hashcheck for the devices (from getDevices())
        @type  ranges: [integer]
        @param ranges: (optional) List of two integers that are the min/max
                       values of a range of uids to include (default: None)
        @type  updates: boolean
        @param updates: (optional) True to lock device from updates (default: False)
        @type  deletion: boolean
        @param deletion: (optional) True to lock device from deletion
                         (default: False)
        @type  sendEvent: boolean
        @param sendEvent: (optional) True to send an event when an action is
                          blocked by locking (default: False)
        @type  uid: string
        @param uid: (optional) Organizer to use when using ranges to get
                    additional uids (default: None)
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       Can be one of the following: name, ipAddress,
                       deviceClass, or productionState (default: None)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return result (default:
                     'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @rtype:   DirectResponse
        @return:  Success or failure message
        """
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        try:
            facade.setLockState(uids, deletion=deletion, updates=updates,
                                sendEvent=sendEvent)
            if not deletion and not updates:
                message = "Unlocked %s devices." % len(uids)
            else:
                actions = []
                if deletion:
                    actions.append('deletion')
                if updates:
                    actions.append('updates')
                message = "Locked %s devices from %s." % (len(uids),
                                                         ' and '.join(actions))
            return DirectResponse.succeed(message)
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to lock devices.')

    @require('Admin Device')
    def resetIp(self, uids, hashcheck, uid=None, ranges=(), params=None,
                sort='name', dir='ASC', ip=''):
        """
        Reset IP address(es) of device(s) to the results of a DNS lookup or
        a manually set address

        @type  uids: [string]
        @param uids: List of device uids with IP's to reset
        @type  hashcheck: string
        @param hashcheck: Hashcheck for the devices (from getDevices())
        @type  uid: string
        @param uid: (optional) Organizer to use when using ranges to get
                    additional uids (default: None)
        @type  ranges: [integer]
        @param ranges: (optional) List of two integers that are the min/max
                       values of a range of uids to include (default: None)
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       Can be one of the following: name, ipAddress,
                       deviceClass, or productionState (default: None)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return result (default:
                     'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @type  ip: string
        @param ip: (optional) IP to set device to. Empty string causes DNS
                   lookup (default: '')
        @rtype:   DirectResponse
        @return:  Success or failure message
        """
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        try:
            for uid in uids:
                info = facade.getInfo(uid)
                info.ipAddress = ip  # Set to empty causes DNS lookup
            return DirectResponse('Reset %s IP addresses.' % len(uids))
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to reset IP addresses.')

    @require('Manage Device')
    def resetCommunity(self, uids, hashcheck, uid=None, ranges=(), params=None,
                      sort='name', dir='ASC'):
        """
        Reset SNMP community string(s) on device(s)

        @type  uids: [string]
        @param uids: List of device uids to reset
        @type  hashcheck: string
        @param hashcheck: Hashcheck for the devices (from getDevices())
        @type  uid: string
        @param uid: (optional) Organizer to use when using ranges to get
                    additional uids (default: None)
        @type  ranges: [integer]
        @param ranges: (optional) List of two integers that are the min/max
                       values of a range of uids to include (default: None)
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       Can be one of the following: name, ipAddress,
                       deviceClass, or productionState (default: None)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return result (default:
                     'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @rtype:   DirectResponse
        @return:  Success or failure message
        """
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        try:
            for uid in uids:
                facade.resetCommunityString(uid)
            return DirectResponse('Reset %s community strings.' % len(uids))
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to reset community strings.')

    @require('Change Device Production State')
    def setProductionState(self, uids, prodState, hashcheck, uid=None,
                           ranges=(), params=None, sort='name', dir='ASC'):
        """
        Set the production state of device(s)

        @type  uids: [string]
        @param uids: List of device uids to set
        @type  prodState: integer
        @param prodState: Production state to set device(s) to.
        @type  hashcheck: string
        @param hashcheck: Hashcheck for the devices (from getDevices())
        @type  uid: string
        @param uid: (optional) Organizer to use when using ranges to get
                    additional uids (default: None)
        @type  ranges: [integer]
        @param ranges: (optional) List of two integers that are the min/max
                       values of a range of uids to include (default: None)
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       Can be one of the following: name, ipAddress,
                       deviceClass, or productionState (default: None)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return result (default:
                     'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @rtype:   DirectResponse
        @return:  Success or failure message
        """
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        try:
            facade.setProductionState(uids, prodState)
            return DirectResponse()
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to change production state.')

    @require('Manage Device')
    def setPriority(self, uids, priority, hashcheck, uid=None, ranges=(),
                    params=None, sort='name', dir='ASC'):
        """
        Set device(s) priority.

        @type  uids: [string]
        @param uids: List of device uids to set
        @type  priority: integer
        @param priority: Priority to set device(s) to.
        @type  hashcheck: string
        @param hashcheck: Hashcheck for the devices (from getDevices())
        @type  uid: string
        @param uid: (optional) Organizer to use when using ranges to get
                    additional uids (default: None)
        @type  ranges: [integer]
        @param ranges: (optional) List of two integers that are the min/max
                       values of a range of uids to include (default: None)
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       Can be one of the following: name, ipAddress,
                       deviceClass, or productionState (default: None)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return result (default:
                     'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @rtype:   DirectResponse
        @return:  Success or failure message
        """
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        try:
            for uid in uids:
                info = facade.getInfo(uid)
                info.priority = priority
            return DirectResponse('Set %s devices to %s priority.' % (
                len(uids), info.priority))
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to change priority.')

    @require('Admin Device')
    def setCollector(self, uids, collector, hashcheck, uid=None, ranges=(),
                     params=None, sort='name', dir='ASC'):
        """
        Set device(s) collector.

        @type  uids: [string]
        @param uids: List of device uids to set
        @type  collector: string
        @param collector: Collector to set devices to
        @type  hashcheck: string
        @param hashcheck: Hashcheck for the devices (from getDevices())
        @type  uid: string
        @param uid: (optional) Organizer to use when using ranges to get
                    additional uids (default: None)
        @type  ranges: [integer]
        @param ranges: (optional) List of two integers that are the min/max
                       values of a range of uids to include (default: None)
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       Can be one of the following: name, ipAddress,
                       deviceClass, or productionState (default: None)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return result (default:
                     'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @rtype:   DirectResponse
        @return:  Success or failure message
        """
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        try:
            for uid in uids:
                info = facade.getInfo(uid)
                info.collector = collector
            return DirectResponse('Changed collector to %s for %s devices.' %
                                  (collector, len(uids)))
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to change the collector.')

    def setComponentsMonitored(self, uids, hashcheck, monitor=False, uid=None,
                               ranges=(), meta_type=None, keys=None,
                               start=0, limit=50, sort='name', dir='ASC',
                               name=None):
        """
        Set the monitoring flag for component(s)

        @type  uids: [string]
        @param uids: List of component uids to set
        @type  hashcheck: string
        @param hashcheck: Hashcheck for the components (from getComponents())
        @type  monitor: boolean
        @param monitor: (optional) True to monitor component (default: False)
        @type  uid: string
        @param uid: (optional) Device to use when using ranges to get
                    additional uids (default: None)
        @type  ranges: [integer]
        @param ranges: (optional) List of two integers that are the min/max
                       values of a range of uids to include (default: None)
        @type  meta_type: string
        @param meta_type: (optional) The meta type of the components to retrieve
                          (default: None)
        @type  keys: [string]
        @param keys: not used
        @type  start: integer
        @param start: (optional) Offset to return the results from; used in
                      pagination (default: 0)
        @type  limit: integer
        @param limit: (optional) Number of items to return; used in pagination
                      (default: 50)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return result (default:
                     'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @type  name: string
        @param name: (optional) Component name to search for when loading ranges
                     (default: None)
        @rtype:   DirectResponse
        @return:  Success or failure message
        """
        if ranges:
            uids += self.loadComponentRanges(ranges, hashcheck, uid, (),
                                             meta_type, start, limit, sort,
                                             dir, name)
        facade = self._getFacade()
        facade.setMonitor(uids, monitor)
        return DirectResponse.succeed(('Set monitoring to %s for %s'
                                       ' components.') % (monitor, len(uids)))

    def lockComponents(self, uids, hashcheck, uid=None, ranges=(),
                       updates=False, deletion=False, sendEvent=False,
                       meta_type=None, keys=None, start=0, limit=50,
                       sort='name', dir='ASC', name=None):
        """
        Lock component(s) from changes.

        @type  uids: [string]
        @param uids: List of component uids to lock
        @type  hashcheck: string
        @param hashcheck: Hashcheck for the components (from getComponents())
        @type  uid: string
        @param uid: (optional) Device to use when using ranges to get
                    additional uids (default: None)
        @type  ranges: [integer]
        @param ranges: (optional) List of two integers that are the min/max
                       values of a range of uids to include (default: None)
        @type  updates: boolean
        @param updates: (optional) True to lock component from updates (default: False)
        @type  deletion: boolean
        @param deletion: (optional) True to lock component from deletion
                         (default: False)
        @type  sendEvent: boolean
        @param sendEvent: (optional) True to send an event when an action is
                          blocked by locking (default: False)
        @type  meta_type: string
        @param meta_type: (optional) The meta type of the components to retrieve
                          (default: None)
        @type  keys: [string]
        @param keys: not used
        @type  start: integer
        @param start: (optional) Offset to return the results from; used in
                      pagination (default: 0)
        @type  limit: integer
        @param limit: (optional) Number of items to return; used in pagination
                      (default: 50)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return result (default:
                     'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @type  name: string
        @param name: (optional) Component name to search for when loading ranges
                     (default: None)
        @rtype:   DirectResponse
        @return:  Success or failure message
        """
        if ranges:
            uids += self.loadComponentRanges(ranges, hashcheck, uid, (),
                                             meta_type, start, limit, sort,
                                             dir, name)
        facade = self._getFacade()
        try:
            facade.setLockState(uids, deletion=deletion, updates=updates,
                                sendEvent=sendEvent)
            if not deletion and not updates:
                message = "Unlocked %d components." % len(uids)
            else:
                actions = []
                if deletion:
                    actions.append('deletion')
                if updates:
                    actions.append('updates')
                actions = ' and '.join(actions)
                message = "Locked %d components from %s." % (len(uids), actions)
            return DirectResponse.succeed(message)
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to lock components.')

    def deleteComponents(self, uids, hashcheck, uid=None, ranges=(),
                         meta_type=None, keys=None, start=0, limit=50,
                         sort='name', dir='ASC', name=None):
        """
        Delete device component(s).

        @type  uids: [string]
        @param uids: List of component uids to delete
        @type  hashcheck: string
        @param hashcheck: Hashcheck for the components (from getComponents())
        @type  uid: string
        @param uid: (optional) Device to use when using ranges to get
                    additional uids (default: None)
        @type  ranges: [integer]
        @param ranges: (optional) List of two integers that are the min/max
                       values of a range of uids to include (default: None)
        @type  meta_type: string
        @param meta_type: (optional) The meta type of the components to retrieve
                          (default: None)
        @type  keys: [string]
        @param keys: not used
        @type  start: integer
        @param start: (optional) Offset to return the results from; used in
                      pagination (default: 0)
        @type  limit: integer
        @param limit: (optional) Number of items to return; used in pagination
                      (default: 50)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return result (default:
                     'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @type  name: string
        @param name: (optional) Component name to search for when loading ranges
                     (default: None)
        @rtype:   DirectResponse
        @return:  Success or failure message
        """
        if ranges:
            uids += self.loadComponentRanges(ranges, hashcheck, uid, (),
                                             meta_type, start, limit, sort,
                                             dir, name)
        facade = self._getFacade()
        try:
            facade.deleteComponents(uids)
            return DirectResponse.succeed('Components deleted.')
        except:
            return DirectResponse.fail('Failed to delete components.')

    @require('Delete Device')
    def removeDevices(self, uids, hashcheck, action="remove", uid=None,
                      ranges=(), params=None, sort='name', dir='ASC'):
        """
        Remove/delete device(s).

        @type  uids: [string]
        @param uids: List of device uids to remove
        @type  hashcheck: string
        @param hashcheck: Hashcheck for the devices (from getDevices())
        @type  action: string
        @param action: Action to take. 'remove' to remove devices from organizer
                       uid, and 'delete' to delete the device from Zenoss.
        @type  uid: string
        @param uid: (optional) Organizer to use when using ranges to get
                    additional uids and/or to remove device (default: None)
        @type  ranges: [integer]
        @param ranges: (optional) List of two integers that are the min/max
                       values of a range of uids to include (default: None)
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       Can be one of the following: name, ipAddress,
                       deviceClass, or productionState (default: None)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return result (default:
                     'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - devtree: ([dictionary]) Object representing the new device tree
             - grptree: ([dictionary]) Object representing the new group tree
             - systree: ([dictionary]) Object representing the new system tree
             - loctree: ([dictionary]) Object representing the new location tree
        """
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        try:
            if action == "remove":
                facade.removeDevices(uids, organizer=uid)
            elif action == "delete":
                facade.deleteDevices(uids)
            return DirectResponse.succeed(
                devtree=self.getTree('/zport/dmd/Devices'),
                grptree=self.getTree('/zport/dmd/Groups'),
                systree=self.getTree('/zport/dmd/Systems'),
                loctree=self.getTree('/zport/dmd/Locations'))
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to remove devices.')

    def getEvents(self, uid):
        """
        Get events for a device.

        @type  uid: [string]
        @param uid: Device to get events for
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - data: ([dictionary]) List of events for a device
        """
        facade = self._getFacade()
        events = facade.getEvents(uid)
        data = Zuul.marshal(events)
        return DirectResponse(data=data)

    def loadRanges(self, ranges, hashcheck, uid=None, params=None,
                      sort='name', dir='ASC'):
        """
        Get a range of device uids.

        @type  ranges: [integer]
        @param ranges: List of two integers that are the min/max values of a
                       range of uids
        @type  hashcheck: string
        @param hashcheck: Hashcheck for the devices (from getDevices())
        @type  uid: string
        @param uid: (optional) Organizer to use to get uids (default: None)
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       Can be one of the following: name, ipAddress,
                       deviceClass, or productionState (default: None)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return result (default:
                     'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @rtype:   [string]
        @return:  A list of device uids
        """
        facade = self._getFacade()
        if isinstance(params, basestring):
            params = unjson(params)
        devs = facade.getDeviceBrains(uid, limit=None, sort=sort, dir=dir,
                                      params=params, hashcheck=hashcheck)
        uids = []
        for start, stop in sorted(ranges):
            uids.extend(b.getPath() for b in islice(devs, start, stop + 1))
        return uids

    def loadComponentRanges(self, ranges, hashcheck, uid=None, types=(),
                            meta_type=(), start=0, limit=None, sort='name',
                            dir='ASC', name=None):
        """
        Get a range of component uids.

        @type  ranges: [integer]
        @param ranges: List of two integers that are the min/max values of a
                       range of uids
        @type  hashcheck: string
        @param hashcheck: not used
        @type  uid: string
        @param uid: (optional) Device to use to get uids (default: None)
        @type  types: [string]
        @param types: (optional) The types of components to retrieve (default: None)
        @type  meta_type: string
        @param meta_type: (optional) The meta type of the components to retrieve
                          (default: None)
        @type  start: integer
        @param start: (optional) Offset to return the results from; used in
                      pagination (default: 0)
        @type  limit: integer
        @param limit: (optional) Number of items to return; used in pagination
                      (default: None)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return result (default:
                     'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @type  name: string
        @param name: (optional) Component name to search for when loading ranges
                     (default: None)
        @rtype:   [string]
        @return:  A list of component uids
        """
        facade = self._getFacade()
        comps = facade.getComponents(uid, types, meta_type, start, limit, sort,
                                     dir, name)
        uids = []
        for start, stop in sorted(ranges):
            uids.extend(b.uid for b in islice(comps, start, stop))
        return uids

    def getUserCommands(self, uid):
        """
        Get a list of user commands for a device uid.

        @type  uid: string
        @param uid: Device to use to get user commands
        @rtype:   [dictionary]
        @return:  List of objects representing user commands
        """
        facade = self._getFacade()
        cmds = facade.getUserCommands(uid)
        return Zuul.marshal(cmds, ['id', 'description'])

    def getProductionStates(self, **kwargs):
        """
        Get a list of available production states.

        @rtype:   [dictionary]
        @return:  List of name/value pairs of available production states
        """
        return DirectResponse(data=[dict(name=s.split(':')[0],
                                         value=s.split(':')[1]) for s in
                                    self.context.dmd.prodStateConversions])

    def getPriorities(self, **kwargs):
        """
        Get a list of available device priorities.

        @rtype:   [dictionary]
        @return:  List of name/value pairs of available device priorities
        """
        return DirectResponse(data=[dict(name=s.split(':')[0],
                                         value=s.split(':')[1]) for s in
                                    self.context.dmd.priorityConversions])

    def getCollectors(self):
        """
        Get a list of available collectors.

        @rtype:   [string]
        @return:  List of collectors
        """
        return self.context.dmd.Monitors.getPerformanceMonitorNames()

    def getDeviceClasses(self, **data):
        """
        Get a list of all device classes.

        @rtype:   DirectResponse
        @return:  B{Properties}:
             - deviceClasses: ([dictionary]) List of device classes
             - totalCount: (integer) Total number of device classes
        """
        devices = self.context.dmd.Devices
        deviceClasses = devices.getOrganizerNames(addblank=True)
        result = [{'name': name} for name in deviceClasses]
        return DirectResponse(deviceClasses=result, totalCount=len(result))
    
    def getSystems(self, **data):
        """
        Get a list of all systems.

        @rtype:   DirectResponse
        @return:  B{Properties}:
             - systems: ([dictionary]) List of systems
             - totalCount: (integer) Total number of systems
        """
        systems = self.context.dmd.Systems.getOrganizerNames()
        result = [{'name': name} for name in systems if name != '/']
        return DirectResponse(systems=result, totalCount=len(result))
    
    def getGroups(self, **data):
        """
        Get a list of all groups.

        @rtype:   DirectResponse
        @return:  B{Properties}:
             - systems: ([dictionary]) List of groups
             - totalCount: (integer) Total number of groups
        """
        groups = self.context.dmd.Groups.getOrganizerNames()
        result = [{'name': name} for name in groups if name != '/']
        return DirectResponse(groups=result, totalCount=len(result))
    
    def getLocations(self, **data):
        """
        Get a list of all locations.

        @rtype:   DirectResponse
        @return:  B{Properties}:
             - systems: ([dictionary]) List of locations
             - totalCount: (integer) Total number of locations
        """
        locations = self.context.dmd.Locations.getOrganizerNames()
        result = [{'name': name} for name in locations if name != '/']
        return DirectResponse(locations=result, totalCount=len(result))

    def getManufacturerNames(self, **data):
        """
        Get a list of all manufacturer names.

        @rtype:   DirectResponse
        @return:  B{Properties}:
             - manufacturers: ([dictionary]) List of manufacturer names
             - totalCount: (integer) Total number of manufacturer names
        """
        names = self.context.dmd.Manufacturers.getManufacturerNames()
        result = [{'name': name} for name in names]
        return DirectResponse(manufacturers=result, totalCount=len(result))

    def getHardwareProductNames(self, manufacturer='', **data):
        """
        Get a list of all hardware product names from a manufacturer.

        @type  manufacturer: string
        @param manufacturer: Manufacturer name
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - productNames: ([dictionary]) List of hardware product names
             - totalCount: (integer) Total number of hardware product names
        """
        manufacturers = self.context.dmd.Manufacturers
        names = manufacturers.getProductNames(manufacturer, 'HardwareClass')
        result = [{'name': name} for name in names]
        return DirectResponse(productNames=result, totalCount=len(result))

    def getOSProductNames(self, manufacturer='', **data):
        """
        Get a list of all OS product names from a manufacturer.

        @type  manufacturer: string
        @param manufacturer: Manufacturer name
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - productNames: ([dictionary]) List of OS product names
             - totalCount: (integer) Total number of OS product names
        """
        manufacturers = self.context.dmd.Manufacturers
        names = manufacturers.getProductNames(manufacturer, 'OS')
        result = [{'name': name} for name in names]
        return DirectResponse(productNames=result, totalCount=len(result))

    def addDevice(self, deviceName, deviceClass, title=None,
                  snmpCommunity="", snmpPort=161,
                  model=False, collector='localhost',  rackSlot=0,
                  productionState=1000, comments="", hwManufacturer="",
                  hwProductName="", osManufacturer="", osProductName="",
                  priority=3, tag="", serialNumber=""):
        """
        Add a device.

        @type  deviceName: string
        @param deviceName: Name or IP of the new device
        @type  deviceClass: string
        @param deviceClass: The device class to add new device to
        @type  title: string
        @param title: (optional) The title of the new device (default: '')
        @type  snmpCommunity: string
        @param snmpCommunity: (optional) A specific community string to use for
                              this device. (default: '')
        @type  snmpPort: integer
        @param snmpPort: (optional) SNMP port on new device (default: 161)
        @type  model: boolean
        @param model: (optional) True to model device at add time (default: False)
        @type  collector: string
        @param collector: (optional) Collector to use for new device (default:
                          localhost)
        @type  rackSlot: string
        @param rackSlot: (optional) Rack slot description (default: '')
        @type  productionState: integer
        @param productionState: (optional) Production state of the new device
                                (default: 1000)
        @type  comments: string
        @param comments: (optional) Comments on this device (default: '')
        @type  hwManufacturer: string
        @param hwManufacturer: (optional) Hardware manufacturer name (default: '')
        @type  hwProductName: string
        @param hwProductName: (optional) Hardware product name (default: '')
        @type  osManufacturer: string
        @param osManufacturer: (optional) OS manufacturer name (default: '')
        @type  osProductName: string
        @param osProductName: (optional) OS product name (default: '')
        @type  priority: integer
        @param priority: (optional) Priority of this device (default: 3)
        @type  tag: string
        @param tag: (optional) Tag number of this device (default: '')
        @type  serialNumber: string
        @param serialNumber: (optional) Serial number of this device (default: '')
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - jobId: (string) ID of the add device job
        """
        # check for permission in the device organizer to which we are
        # adding the device
        facade = self._getFacade()
        organizer = facade._getObject('/zport/dmd/Devices' + deviceClass)
        if not Zuul.checkPermission("Manage Device", organizer):
            raise Unauthorized('Calling AddDevice requires ' +
                               'Manage Device permission on %s' % deviceClass)
        jobStatus = self._getFacade().addDevice(deviceName,
                                               deviceClass,
                                               title,
                                               snmpCommunity,
                                               snmpPort,
                                               model,
                                               collector,
                                               rackSlot,
                                               productionState,
                                               comments,
                                               hwManufacturer,
                                               hwProductName,
                                               osManufacturer,
                                               osProductName,
                                               priority,
                                               tag,
                                               serialNumber)
        return DirectResponse.succeed(jobId=jobStatus.id)

    @require('Manage Device')
    def remodel(self, deviceUid):
        """
        Submit a job to have a device remodeled.

        @type  deviceUid: string
        @param deviceUid: Device uid to have local template
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - jobId: (string) ID of the add device job
        """
        jobStatus = self._getFacade().remodel(deviceUid)
        return DirectResponse.succeed(jobId=jobStatus.id)

    @require('Edit Local Templates')
    def addLocalTemplate(self, deviceUid, templateId):
        """
        Adds a local template on a device.

        @type  deviceUid: string
        @param deviceUid: Device uid to have local template
        @type  templateId: string
        @param templateId: Name of the new template
        @rtype:  DirectResponse
        @return: Success message
        """
        facade = self._getFacade()
        facade.addLocalTemplate(deviceUid, templateId)
        return DirectResponse.succeed()

    @require('Edit Local Templates')
    def removeLocalTemplate(self, deviceUid, templateUid):
        """
        Removes a locally defined template on a device.

        @type  deviceUid: string
        @param deviceUid: Device uid that has local template
        @type  templateUid: string
        @param templateUid: Name of the template to remove
        @rtype:  DirectResponse
        @return: Success message
        """
        facade = self._getFacade()
        facade.removeLocalTemplate(deviceUid, templateUid)
        return DirectResponse.succeed()

    def getLocalTemplates(self, query, uid):
        """
        Get a list of locally defined templates on a device.

        @type  query: string
        @param query: not used
        @type  uid: string
        @param uid: Device uid to query for templates
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - data: ([dictionary]) List of objects representing local templates
        """
        facade = self._getFacade()
        templates = facade.getLocalTemplates(uid)
        data = []
        for template in templates:
            data.append(dict(label=template['text'], uid=template['uid']))
        return DirectResponse.succeed(data=data)

    def getTemplates(self, id):
        """
        Get a list of available templates for a device.

        @type  id: string
        @param id: Device uid to query for templates
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - data: ([dictionary]) List of objects representing templates
        """
        facade = self._getFacade()
        templates = facade.getTemplates(id)
        return Zuul.marshal(templates)

    def getUnboundTemplates(self, uid):
        """
        Get a list of unbound templates for a device.

        @type  uid: string
        @param uid: Device uid to query for templates
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - data: ([dictionary]) List of objects representing templates
        """
        facade = self._getFacade()
        templates = facade.getUnboundTemplates(uid)
        data = []
        for template in templates:
            label = '%s (%s)' % (template.titleOrId(), template.getUIPath())
            data.append([template.id, label])
        return DirectResponse.succeed(data=Zuul.marshal(data))

    def getBoundTemplates(self, uid):
        """
        Get a list of bound templates for a device.

        @type  uid: string
        @param uid: Device uid to query for templates
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - data: ([dictionary]) List of objects representing templates
        """
        facade = self._getFacade()
        templates = facade.getBoundTemplates(uid)
        data = []
        for template in templates:
            label = '%s (%s)' % (template.titleOrId(), template.getUIPath())
            data.append([template.id, label])
        return DirectResponse.succeed(data=Zuul.marshal(data))

    @require('Edit Local Templates')
    def setBoundTemplates(self, uid, templateIds):
        """
        Set a list of templates as bound to a device.

        @type  uid: string
        @param uid: Device uid to bind templates to
        @type  templateIds: [string]
        @param templateIds: List of template uids to bind to device
        @rtype:   DirectResponse
        @return:  Success message
        """
        facade = self._getFacade()
        facade.setBoundTemplates(uid, templateIds)
        return DirectResponse.succeed()

    @require('Edit Local Templates')
    def resetBoundTemplates(self, uid):
        """
        Remove all bound templates from a device.

        @type  uid: string
        @param uid: Device uid to remove bound templates from
        @rtype:   DirectResponse
        @return:  Success message
        """
        facade = self._getFacade()
        facade.resetBoundTemplates(uid)
        return DirectResponse.succeed()

    @require('Edit Local Templates')
    def bindOrUnbindTemplate(self, uid, templateUid):
        """
        Bind an unbound template or unbind a bound template from a device.

        @type  uid: string
        @param uid: Device uid to bind/unbind template
        @type  templateUid: string
        @param templateUid: Template uid to bind/unbind
        @rtype:   DirectResponse
        @return:  Success message
        """
        facade = self._getFacade()
        template = facade._getObject(templateUid)
        templateIds = [t.id for t in facade.getBoundTemplates(uid)]
        # not bound
        if not template.id in templateIds:
            self.setBoundTemplates(uid, templateIds + [template.id])
        else:
            # already bound so unbind it
            templateIds = [t for t in templateIds if t != template.id]
            self.setBoundTemplates(uid, templateIds)
        return DirectResponse.succeed()

    def getOverridableTemplates(self, query, uid):
        """
        Get a list of available templates on a device that can be overridden.

        @type  query: string
        @param query: not used
        @type  uid: string
        @param uid: Device to query for overridable templates
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - data: ([dictionary]) List of objects representing templates
        """
        facade = self._getFacade()
        templates = facade.getOverridableTemplates(uid)
        # we just need the text and the id (for our combobox)
        data = []
        for template in templates:
            label = '%s (%s)' % (template.text, template.getUIPath())
            data.append(dict(label=label, uid=template.uid))
        return DirectResponse.succeed(data=data)

    @require('Manage DMD')
    def clearGeocodeCache(self):
        """
        Clear the Google Maps geocode cache.

        @rtype:   DirectResponse
        @return:  Success message
        """
        self.context.clearGeocodeCache()
        return DirectResponse.succeed()
