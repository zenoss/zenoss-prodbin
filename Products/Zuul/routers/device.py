##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


"""
Operations for Device Organizers and Devices.

Available at:  /zport/dmd/device_router
"""
import logging
from itertools import islice
from AccessControl import Unauthorized
from Products.ZenUtils.Ext import DirectResponse
from Products.ZenUtils.Utils import getDisplayType
from Products.ZenUtils.jsonutils import unjson
from Products import Zuul
from Products.ZenModel.Device import Device
from Products.ZenModel.ZenossSecurity import ZEN_CHANGE_DEVICE_PRODSTATE, ZEN_MANAGE_DMD, \
    ZEN_ADMIN_DEVICE, ZEN_MANAGE_DEVICE, ZEN_DELETE_DEVICE
from Products.Zuul import filterUidsByPermission
from Products.Zuul.routers import TreeRouter
from Products.Zuul.exceptions import DatapointNameConfict
from Products.Zuul.catalog.events import IndexingEvent
from Products.Zuul.form.interfaces import IFormBuilder
from Products.Zuul.decorators import require, serviceConnectionError
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier, IGUIDManager
from Products.ZenMessaging.audit import audit
from zope.event import notify

log = logging.getLogger('zen.Zuul')

class DeviceRouter(TreeRouter):
    """
    A JSON/ExtDirect interface to operations on devices
    """

    @serviceConnectionError
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
        facade = self._getFacade()
        organizer = facade.addLocationOrganizer(contextUid,
                                                id,
                                                description,
                                                address)
        uid = organizer.uid

        treeNode = facade.getTree(uid)
        audit('UI.Location.Add', uid, description=description, address=address)
        return DirectResponse.succeed("Location added", nodeConfig=Zuul.marshal(treeNode))

    def _getFacade(self):
        return Zuul.getFacade('device', self.context)

    @serviceConnectionError
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

    @serviceConnectionError
    def getComponents(self, uid=None, meta_type=None, keys=None, start=0,
                      limit=50, page=0, sort='name', dir='ASC', name=None):
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
        if name:
            # Load every component if we have a filter
            limit = None
        comps = facade.getComponents(uid, meta_type=meta_type, start=start,
                                     limit=limit, sort=sort, dir=dir, name=name, keys=keys)
        total = comps.total
        hash = comps.hash_

        data = Zuul.marshal(comps, keys=keys)
        return DirectResponse(data=data, totalCount=total,
                              hash=hash)

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

    @serviceConnectionError
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

    @serviceConnectionError
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

    @serviceConnectionError
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
        the_uid = data['uid']  # gets deleted
        process = facade.getInfo(the_uid)
        oldData = self._getInfoData(process, data.keys())
        Zuul.unmarshal(data, process)
        newData = self._getInfoData(process, data.keys())
        # reindex the object if necessary
        if hasattr(process._object, 'index_object'):
            process._object.index_object()

        # Ex: ('UI.Device.Edit', uid, data_={'productionState': 'High'})
        # Ex: ('UI.Location.Edit', uid, description='Blah', old_description='Foo')
        if 'name' in oldData:
            oldData['device_name'] = oldData['name']  # we call it this now
            del oldData['name']
        if 'name' in newData:
            del newData['name']  # it gets printed automatically
        if isinstance(process._object, Device):
            # ZEN-2837, ZEN-247: Audit names instead of numbers
            dmd = self.context
            if 'productionState' in oldData:
                oldData['productionState'] = dmd.convertProdState(oldData['productionState'])
            if 'productionState' in newData:
                newData['productionState'] = dmd.convertProdState(newData['productionState'])
            if 'priority' in oldData:
                oldData['priority'] = dmd.convertPriority(oldData['priority'])
            if 'priority' in newData:
                newData['priority'] = dmd.convertPriority(newData['priority'])
        audit(['UI', getDisplayType(process._object), 'Edit'], the_uid,
              data_=newData, oldData_=oldData, skipFields_='uid')
        return DirectResponse.succeed()

    def _getInfoData(self, info, keys):
        # TODO: generalize this code for all object types, if possible.
        values = {}
        for key in keys:
            val = getattr(info, key, None)
            if val is not None:
                values[key] = str(val)  # unmutable copy
        return values

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
        audit('UI.Device.Edit', uid, data_=data)
        return DirectResponse()

    def getDeviceUuidsByName(self, query="", start=0, limit=25, page=1, uuid=None):
        """
        Retrieves a list of device uuids. For use in combos.
        If uuid is set, ensures that it is included in the returned list.
        """
        facade = self._getFacade()
        devices = facade.getDevices(params={'name':query}) # TODO: pass start=start, limit=limit
        result = [{'name':dev.name,
                   'uuid':IGlobalIdentifier(dev._object).getGUID()}
                  for dev in devices]

        if uuid and uuid not in (device['uuid'] for device in result):
            guidManager = IGUIDManager(self.context.dmd)
            device = guidManager.getObject(uuid)
            if device:
                result.append({'name':device.name(), 'uuid':uuid})

        return DirectResponse.succeed(data=result)

    def getDeviceUids(self, uid):
        """
        Return a list of device uids underneath an organizer. This includes
        all the devices belonging to an child organizers.

        @type  uid: string
        @param uid: Unique identifier of the organizer to get devices from
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - devices: (list) device uids
        """
        facade = self._getFacade()
        uids = facade.getDeviceUids(uid)
        return DirectResponse.succeed(devices=uids)

    @serviceConnectionError
    def getDevices(self, uid=None, start=0, params=None, limit=50, sort='name',
                   page=None,
                   dir='ASC', keys=None):
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
        allKeys = ['name', 'ipAddress', 'productionState', 'events',
                   'ipAddressString', 'serialNumber', 'tagNumber',
                   'hwManufacturer', 'hwModel', 'osModel', 'osManufacturer',
                   'collector', 'priority', 'systems', 'groups', 'location',
                   'pythonClass', 'tagNumber', 'serialNumber',
                   'hwModel', 'hwManufacturer',
                   'osModel', 'osManufacturer',
                   'groups', 'systems', 'location']
        usedKeys = keys or allKeys
        if not 'uid' in usedKeys:
            usedKeys.append('uid')

        data = Zuul.marshal(devices.results, usedKeys)

        return DirectResponse(devices=data, totalCount=devices.total,
                              hash=devices.hash_)

    def renameDevice(self, uid, newId):
        """
        Set the device specified by the uid,"uid" to have the
        the id "newId"
        This will raise an exception if it fails.

        @type  uid: string
        @param uid: The unique id of the device we are renaming
        @type  newId: string
        @param newId: string of the new id
        """
        facade = self._getFacade()
        newUid = facade.renameDevice(uid, newId)
        return DirectResponse.succeed(uid=newUid)

    def moveDevices(self, uids, target, hashcheck=None, ranges=(), uid=None,
                    params=None, sort='name', dir='ASC', asynchronous=True):
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
        uids = filterUidsByPermission(self.context.dmd, ZEN_MANAGE_DEVICE, uids)
        facade = self._getFacade()

        # In order to display the device name and old location/device class,
        # we must audit first. This means it's possible we can audit a change
        # then the command fails, unfortunately.
        # example: audit('UI.Device.ChangeLocation', uid, location=..., old_location=...)
        targetType = getDisplayType(facade._getObject(target))
        autoRemovalTypes = ('DeviceClass', 'Location')
        action = ('Change' if targetType in autoRemovalTypes else 'AddTo') + targetType
        for uid in uids:
            oldData = {}
            if targetType == 'Location':  # get old location
                location = facade._getObject(uid).location()
                locationPath = location.getPrimaryId() if location else ''
                oldData[targetType] = locationPath
            elif targetType == 'DeviceClass':
                deviceClass = facade._getObject(uid).deviceClass()
                deviceClassPath = deviceClass.getPrimaryId() if deviceClass else ''
                oldData[targetType] = deviceClassPath
            audit(['UI.Device', action], uid,
                  data_={targetType:target}, oldData_=oldData)
        try:
            result = facade.moveDevices(uids, target, asynchronous=asynchronous)
        except Exception, e:
            log.exception("Failed to move devices")
            return DirectResponse.exception(e, 'Failed to move devices.')
        if asynchronous:
            return DirectResponse.succeed(new_jobs=Zuul.marshal([result],
                                  keys=('uuid', 'description', 'started')))
        else:
            return DirectResponse.succeed(exports=result)

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
        for uid in uids:
            audit('UI.Device.PushChanges', uid)
        return DirectResponse.succeed('Changes pushed to collectors.')

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
        uids = filterUidsByPermission(self.context.dmd, ZEN_MANAGE_DMD, uids)
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
            for uid in uids:
                audit('UI.Device.EditLocks', uid,
                      deletion=deletion, updates=updates, sendEvent=sendEvent)
            return DirectResponse.succeed(message)
        except Exception, e:
            log.exception(e)
            return DirectResponse.exception(e, 'Failed to lock devices.')


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
        uids = filterUidsByPermission(self.context.dmd, ZEN_ADMIN_DEVICE, uids)
        try:
            for uid in uids:
                info = facade.getInfo(uid)
                info.ipAddress = ip  # Set to empty causes DNS lookup
                audit('UI.Device.ResetIP', uid, ip=ip)
            return DirectResponse('Reset %s IP addresses.' % len(uids))
        except Exception, e:
            log.exception(e)
            return DirectResponse.exception(e, 'Failed to reset IP addresses.')

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
                audit('UI.Device.ResetCommunity', uid)
            return DirectResponse('Reset %s community strings.' % len(uids))
        except Exception, e:
            log.exception(e)
            return DirectResponse.exception(e, 'Failed to reset community strings.')

    def setProductionState(self, uids, prodState, hashcheck, uid=None,
                           ranges=(), params=None, sort='name', dir='ASC'):
        """
        Set the production state of device(s).

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
        uids = filterUidsByPermission(self.context.dmd, ZEN_CHANGE_DEVICE_PRODSTATE,
                                      uids)
        try:
            oldStates = {}
            uids = (uids,) if isinstance(uids, basestring) else uids
            for uid in uids:
                device = facade._getObject(uid)
                if isinstance(device, Device):
                    oldStates[uid] = self.context.convertProdState(device.productionState)

            facade.setProductionState(uids, prodState)
            prodStateName = self.context.convertProdState(prodState)

            auditData = {'productionState': prodStateName}
            for uid in uids:
                oldAuditData = {'productionState': oldStates[uid]}
                audit('UI.Device.Edit', uid, oldData_=oldAuditData, data_=auditData)
            return DirectResponse('Set %s devices to %s.' % (
                len(uids), prodStateName))
        except Exception, e:
            log.exception(e)
            return DirectResponse.exception(e, 'Failed to change production state.')

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
        uids = filterUidsByPermission(self.context.dmd, ZEN_MANAGE_DEVICE, uids)
        try:
            for uid in uids:
                info = facade.getInfo(uid)
                oldPriorityLabel = info.priorityLabel
                info.priority = priority
                notify(IndexingEvent(info._object))
                audit('UI.Device.Edit', uid,
                      priority=info.priorityLabel,
                      oldData_={'priority':oldPriorityLabel})
            return DirectResponse('Set %s devices to %s priority.' % (
                len(uids), info.priorityLabel))
        except Exception, e:
            log.exception(e)
            return DirectResponse.exception(e, 'Failed to change priority.')

    def setCollector(self, uids, collector, hashcheck, uid=None, ranges=(),
                     params=None, sort='name', dir='ASC', moveData=False,
                     asynchronous=True):
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
        uids = filterUidsByPermission(self.context.dmd, ZEN_ADMIN_DEVICE, uids)
        try:
            # iterate through uids so that logging works as expected
            result = facade.setCollector(uids, collector, moveData, asynchronous)
            for devUid in uids:
                audit('UI.Device.ChangeCollector', devUid, collector=collector)
            if asynchronous and result:
                return DirectResponse.succeed(new_jobs=Zuul.marshal(result,
                                      keys=('uuid', 'description', 'started')))
            else:
                return DirectResponse.succeed('Changed collector to %s for %s devices.' %
                                      (collector, len(uids)))
        except Exception, e:
            log.exception(e)
            return DirectResponse.exception(e, 'Failed to change the collector.')

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
        action = 'SetMonitored' if monitor else 'SetUnmonitored'
        for uid in uids:
            audit(['UI.Component', action], uid)
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
            for uid in uids:
                audit('UI.Component.EditLocks', uid,
                      deletion=deletion, updates=updates, sendEvents=sendEvent)
            return DirectResponse.succeed(message)
        except Exception, e:
            log.exception(e)
            return DirectResponse.exception(e, 'Failed to lock components.')

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
            for uid in uids:
                audit('UI.Component.Delete', uid)
            return DirectResponse.succeed('Components deleted.')
        except Exception, e:
            return DirectResponse.exception(e, 'Failed to delete components.')

    def removeDevices(self, uids, hashcheck, action="remove", uid=None,
                      ranges=(), params=None, sort='name', dir='ASC',
                      deleteEvents=False, deletePerf=False
                      ):
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
        @type  deleteEvents: bool
        @param deleteEvents: will remove all the events for the devices as well
        @type  deletePerf: bool
        @param deletePerf: will remove all the perf data for the devices
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
        removedUids = tuple()
        uids = filterUidsByPermission(self.context.dmd, ZEN_DELETE_DEVICE, uids)
        try:
            if action == "remove":
                removed = facade.removeDevices(uids, organizer=uid)

                # uid could be an object or string.
                organizer = facade._getObject(uid) if isinstance(uid, basestring) else uid
                organizerType = organizer.meta_type
                action = 'RemoveFrom' + organizerType   # Ex: RemoveFromLocation
                removedUids = map(lambda x: x.uid, removed)
                for devuid in removedUids:
                    # Ex: ('UI.Device.RemoveFromLocation', deviceUid, location=...)
                    audit('UI.Device.%s' % action, devuid, data_={organizerType:uid})
                notRemovedUids = list(set(uids) - set(removedUids))
                return DirectResponse.succeed(
                    removedUids=removedUids,
                    notRemovedUids=notRemovedUids)
            elif action == "delete":
                for devuid in uids:
                    audit('UI.Device.Delete', devuid,
                          deleteEvents=deleteEvents,
                          deletePerf=deletePerf)
                    facade.deleteDevices(uids,
                                         deleteEvents=deleteEvents,
                                         deletePerf=deletePerf)
                return DirectResponse.succeed()
        except Exception, e:
            log.exception(e)
            return DirectResponse.exception(e, 'Failed to remove devices.')

    @serviceConnectionError
    def getGraphDefs(self, uid, drange=None):
        """
        Returns the url and title for each graph
        for the object passed in.
        @type  uid: string
        @param uid: unique identifier of an object
        """
        facade = self._getFacade()
        data = facade.getGraphDefs(uid, drange)
        return DirectResponse(data=Zuul.marshal(data))

    @serviceConnectionError
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
        if uid is None:
            uid = "/".join(self.context.getPhysicalPath())
        facade = self._getFacade()
        comps = facade.getComponents(uid, types, meta_type, start, limit, sort,
                                     dir, name)
        uids = []
        for start, stop in sorted(ranges):
            uids.extend(b.uid for b in islice(comps, start, stop))
        return uids

    @serviceConnectionError
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
                                         value=int(s.split(':')[1])) for s in
                                    self.context.dmd.prodStateConversions])

    def getPriorities(self, **kwargs):
        """
        Get a list of available device priorities.

        @rtype:   [dictionary]
        @return:  List of name/value pairs of available device priorities
        """
        return DirectResponse(data=[dict(name=s.split(':')[0],
                                         value=int(s.split(':')[1])) for s in
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
                  snmpCommunity="", snmpPort=161, manageIp="",
                  model=False, collector='localhost',  rackSlot=0,
                  locationPath="", systemPaths=[], groupPaths=[],
                  productionState=1000, comments="", hwManufacturer="",
                  hwProductName="", osManufacturer="", osProductName="",
                  priority=3, tag="", serialNumber="", zCommandUsername="",
                  zCommandPassword="", zWinUser="", zWinPassword="",
                  zProperties={}, cProperties={},):

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
        @type  manageIp: string
        @param manageIp: (optional) Management IP address on new device (default:
                         empty/derive from DNS)
        @type  locationPath: string
        @param locationPath: (optional) Organizer path of the location for this device
        @type  systemPaths: List (strings)
        @param systemPaths: (optional) List of organizer paths for the device
        @type  groupPaths: List (strings)
        @param groupPaths: (optional) List of organizer paths for the device
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
        @type  zCommandUsername: string
        @param zWinUser: (optional) Username for WMI (default: '')
        @type  zCommandPassword: string
        @param zWinPassword: (optional) Password for WMI (default: '')
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - jobId: (string) ID of the add device job
        """
        # check for permission in the device organizer to which we are
        # adding the device
        facade = self._getFacade()
        organizerUid = '/zport/dmd/Devices' + deviceClass
        organizer = facade._getObject(organizerUid)
        if not Zuul.checkPermission("Manage Device", organizer):
            raise Unauthorized('Calling AddDevice requires ' +
                               'Manage Device permission on %s' % deviceClass)

        if title is None:
            title = deviceName

        # the device name is used as part of the URL, so any unicode characters
        # will be stripped before saving. Pre-empt this and make the device name
        # safe prior to the uniqueness check.
        safeDeviceName = organizer.prepId(deviceName)

        device = facade.getDeviceByIpAddress(safeDeviceName, collector, manageIp)
        if device:
            return DirectResponse.fail(deviceUid=device.getPrimaryId(),
                                       msg="Device %s already exists. <a href='%s'>Go to the device</a>" % (deviceName, device.getPrimaryId()))

        if isinstance(systemPaths, basestring):
            systemPaths = [systemPaths]
        if isinstance(groupPaths, basestring):
            groupPaths = [groupPaths]

        jobrecords = self._getFacade().addDevice(deviceName,
                                               deviceClass,
                                               title,
                                               snmpCommunity,
                                               snmpPort,
                                               manageIp,
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
                                               serialNumber,
                                               locationPath,
                                               zCommandUsername,
                                               zCommandPassword,
                                               zWinUser,
                                               zWinPassword,
                                               systemPaths,
                                               groupPaths,
                                               zProperties,
                                               cProperties,
                                               )

        deviceUid = '/'.join([organizerUid, 'devices', deviceName])
        # Zero groups or systems sends as [''] so exclude that case.
        hasGroups = len(groupPaths) > 1 or (groupPaths and groupPaths[0])
        hasSystems = len(systemPaths) > 1 or (systemPaths and systemPaths[0])
        auditData = {
            'deviceClass': '/Devices' + deviceClass,
            'location': '/Locations' + locationPath if locationPath else None,
            'deviceGroups': ['/Groups' + x for x in groupPaths] if hasGroups else None,
            'systems': ['/Systems' + x for x in systemPaths] if hasSystems else None,
            'device_name': title if title else deviceName, # see Trac #30109
            'collector': collector,
            'model': str(model),  # show value even if False
            'productionState': self.context.convertProdState(productionState),
            'priority': self.context.convertPriority(priority),
        }
        audit('UI.Device.Add', deviceUid, data_=auditData)
        return DirectResponse.succeed(new_jobs=Zuul.marshal(jobrecords, keys=('uuid', 'description')))

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
        audit('UI.Device.Remodel', deviceUid)
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
        audit('UI.Device.AddLocalTemplate', deviceUid, template=templateId)
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
        audit('UI.Device.RemoveLocalTemplate', deviceUid, template=templateUid)
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

    @serviceConnectionError
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

    @serviceConnectionError
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

    @serviceConnectionError
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
        try:
            facade.setBoundTemplates(uid, templateIds)
        except DatapointNameConfict, e:
            log.info("Failed to bind templates for {}: {}".format(uid, e))
            return DirectResponse.exception(e, 'Failed to bind templates.')
        audit('UI.Device.BindTemplates', uid, templates=templateIds)
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
        audit('UI.Device.ResetBoundTemplates', uid)
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
            audit('UI.Device.BindTemplate', uid, template=templateUid)
        else:
            # already bound so unbind it
            templateIds = [t for t in templateIds if t != template.id]
            self.setBoundTemplates(uid, templateIds)
            audit('UI.Device.UnbindTemplate', uid, template=templateUid)
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
        facade = self._getFacade()
        facade.clearGeocodeCache()
        audit('UI.GeocodeCache.Clear')
        return DirectResponse.succeed()

    @serviceConnectionError
    def getModelerPluginDocStrings(self, uid):
        """
        Given a uid returns the documentation for all the modeler plugins.
        """
        facade = self._getFacade()
        data = facade.getModelerPluginDocStrings(uid)
        return DirectResponse.succeed(data=Zuul.marshal(data))

    def addIpRouteEntry(self, uid, dest='', routemask='', nexthopid='', interface='',
                        routeproto='', routetype='', userCreated=True):
        """
        Adds an Ip Route Entry to this device
        """
        facade = self._getFacade()
        data = facade.addIpRouteEntry(uid, dest, routemask, nexthopid, interface,
                        routeproto, routetype, userCreated)
        return DirectResponse.succeed(data=Zuul.marshal(data))

    def addIpInterface(self, uid, newId, userCreated=True):
        """
        Adds an Ip Interface
        """
        facade = self._getFacade()
        data = facade.addIpInterface(uid, newId, userCreated)
        return DirectResponse.succeed(data=Zuul.marshal(data))

    def addOSProcess(self, uid, newClassName, userCreated=True):
        """
        Adds an os processes
        """
        facade = self._getFacade()
        data = facade.addOSProcess(uid, newClassName, userCreated)
        return DirectResponse.succeed(data=Zuul.marshal(data))

    def addFileSystem(self, uid, newId, userCreated=True):
        """
        Adds an Ip Interface
        """
        facade = self._getFacade()
        data = facade.addFileSystem(uid, newId, userCreated)
        return DirectResponse.succeed(data=Zuul.marshal(data))

    def addIpService(self, uid, newClassName, protocol, userCreated=True):
        """
        Adds an Ip Service
        """
        facade = self._getFacade()
        data = facade.addIpService(uid, newClassName, protocol,  userCreated)
        return DirectResponse.succeed(data=Zuul.marshal(data))


    def addWinService(self, uid, newClassName, userCreated=True):
        """
        Adds an Ip Service
        """
        facade = self._getFacade()
        data = facade.addWinService(uid, newClassName, userCreated)
        return DirectResponse.succeed(data=Zuul.marshal(data))

    def getSoftware(self, uid, keys=None):

        facade = self._getFacade()
        software = facade.getSoftware(uid)
        return DirectResponse(data=Zuul.marshal(software, keys))

    def getOverriddenObjectsList(self, uid, propname, relName):
        """
        returns a list of Overridden Objects and properties for this context
        """
        facade = self._getFacade()
        data = facade.getOverriddenObjectsList(uid, propname, relName)
        return DirectResponse.succeed(data=Zuul.marshal(data))

    def getOverriddenObjectsParent(self, uid, propname=''):
        """
        returns the base of the Overridden Objects
        """
        facade = self._getFacade()
        data = facade.getOverriddenObjectsParent(uid, propname)
        return DirectResponse.succeed(data=Zuul.marshal(data))

    def getOverriddenZprops(self, uid, all=True, pfilt=''):
        """
        returns a list of zProperty values for the overridden objects
        """
        facade = self._getFacade()
        data = facade.getOverriddenZprops(uid, all)
        return DirectResponse.succeed(data=Zuul.marshal(data))
