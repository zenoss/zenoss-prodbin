
#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""DeviceGroupBase

DeviceGroupBase interface for device grouping objects
it implements some generic forms of its functions that
DeviceGroupers can use.

$Id: DeviceGroupBase.py,v 1.6 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.6 $"[11:-2]
        
from Products.ZenUtils.Utils import travAndColl

class DeviceGroupBase:
    """DeviceGroupBase object"""
    
    def getSubDevices(self, devfilter=None, 
                    subrel="subgroups", devrel="devices"):
        """get all the devices under and instance of a DeviceGroup"""
        devices = getattr(self, devrel, None)
        if not devices: 
            raise AttributeError, "%s not found on %s" % (devrel, self.id)
        devices = filter(devfilter, devices())
        subgroups = getattr(self, subrel, None)
        if not subgroups: 
            raise AttributeError, "%s not found on %s" % (subrel, self.id)
        for subgroup in subgroups():
            devices.extend(subgroup.getSubDevices(devfilter))
        return devices


    def getDeviceGroup(self, path, rootName, factory, relpath):
        """return and potentially create a device group from its path"""
        path = self.zenpathsplit(path)
        if path[0] != rootName: path.insert(0,rootName)
        name = self.zenpathjoin(path)
        return self.getHierarchyObj(self.getDmd(), name, factory, 
                                    relpath=relpath)


    def getDeviceGroupName(self, rootName="", superrel="parent"):
        """get the full path of a group without its subrel names"""
        fullName = travAndColl(self, superrel, [], 'id')
        fullName.reverse()
        if rootName: fullName.remove(rootName)
        return self.zenpathjoin(fullName)
    
    getPathName = getDeviceGroupName


    def getDeviceGroupNames(self, rootName="", subrel="subgroups"):
        """return the full paths to all subgroups"""
        groupNames = []
        if self.id != rootName:
            groupNames.append(self.getDeviceGroupName(rootName))
        subgroups = getattr(self, subrel, None)
        if not subgroups: 
            raise AttributeError, "%s not found on %s" % (subrel, self.id)
        for subgroup in subgroups():
            groupNames.extend(subgroup.getDeviceGroupNames(rootName, subrel))
        if self.id == rootName: 
            groupNames.sort(lambda x,y: cmp(x.lower(), y.lower()))
        return groupNames


    def getAllCounts(self, subrel="subgroups", devrel="devices"):
        """Count all devices within a device group and get the
        ping and snmp counts as well"""
        counts = [
            self.devices.countObjects(),
            self._status("Ping", devrel),
            self._status("Snmp", devrel),
        ]
        subgroups = getattr(self, subrel, None)
        if not subgroups: 
            raise AttributeError, "%s not found on %s" % (subrel, self.id)
        for group in subgroups():
            sc = group.getAllCounts()
            for i in range(3): counts[i] += sc[i]
        return counts


    def countDevices(self, subrel="subgroups", devrel="devices"):
        """count all devices with in a device group"""
        count = self.devices.countObjects()
        subgroups = getattr(self, subrel, None)
        if not subgroups: 
            raise AttributeError, "%s not found on %s" % (subrel, self.id)
        for group in subgroups():
            count += group.countDevices()
        return count


    def pingStatus(self, subrel="subgroups", devrel="devices"):
        """aggrigate ping status for all devices in this group and below"""
        status = self._status("Ping", devrel)
        subgroups = getattr(self, subrel, None)
        if not subgroups: 
            raise AttributeError, "%s not found on %s" % (subrel, self.id)
        for group in subgroups():
            status += group.pingStatus()
        return status

    
    def snmpStatus(self, subrel="subgroups", devrel="devices"):
        """aggrigate snmp status for all devices in this group and below"""
        status = self._status("Snmp", devrel)
        subgroups = getattr(self, subrel, None)
        if not subgroups: 
            raise AttributeError, "%s not found on %s" % (subrel, self.id)
        for group in subgroups():
            status += group.snmpStatus()
        return status


    def _status(self, type, devrel="devices"):
        """build status info for device in this device group"""
        status = 0
        statatt = "get%sStatusNumber" % type
        devices = getattr(self, devrel, None)
        if not devices: 
            raise AttributeError, "%s not found on %s" % (devrel, self.id)
        for device in devices():
            if getattr(device, statatt, -1)() > 0:
                status += 1
        return status
    
    
    def getDeviceGroupOmnibusEvents(self, omniField):
        """get omnibus events for this device group"""
        self.REQUEST.set('ev_whereclause', 
            "%s like '.*%s.*'" % (omniField, self.getDeviceGroupName()))
        return self.viewEvents(self.REQUEST)


    def getDeviceGroupOmnibusHistoryEvents(self, omniField):
        """get the history event list of this object"""
        self.REQUEST.set('ev_whereclause', 
            "%s like '%%%s%%'" % (omniField, self.getDeviceGroupName()))
        self.REQUEST.set('ev_orderby', "LastOccurrence desc")
        return self.viewHistoryEvents(self.REQUEST)


    def statusColor(self, status):
        """colors for status fields for device groups"""
        retval = '#00ff00'
        if status == -1:
            retval = "#d02090"
        elif status == 1:
            retval = '#ffff00'
        elif status == 2:
            retval = '#ff9900'
        elif status > 2:
            retval = '#ff0000'
        return retval


    #security.declareProtected('View', 'helpLink')
    def helpLink(self):
        '''return a link to the objects help file'''
        path = self.__class__.__module__.split('.')
        className = path[-1].replace('Class','')
        product = path[-2]
       
        path = ("", "Control_Panel", "Products", product, "Help", 
                "%s.stx"%className)

        # check to see if we have a help screen
        app = self.getPhysicalRoot()
        try:
            app.restrictedTraverse(path)
        except KeyError:
            return ""
            
        url = "/HelpSys?help_url="+ "/".join(path)

        return """<a class="tabletitle" href="%s"
            onClick="window.open('%s','zope_help','width=600,height=500,
            menubar=yes,toolbar=yes,scrollbars=yes,resizable=yes'); 
            return false;" onMouseOver="window.status='Open online help'; 
            return true;" onMouseOut="window.status=''; return true;">Help!</a>
            """ % (url, url)
             
