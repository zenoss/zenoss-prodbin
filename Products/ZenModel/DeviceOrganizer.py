
#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""DeviceOrganizer

$Id: DeviceOrganizer.py,v 1.6 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.6 $"[11:-2]

from Products.ZenModel.Organizer import Organizer

class DeviceOrganizer(Organizer):
    """
    DeviceOrganizer is the base class for device organizers.
    It has lots of methods for rolling up device statistics and information.
    """
    
    def getSubDevices(self, devfilter=None, devrel="devices"):
        """get all the devices under and instance of a DeviceGroup"""
        devices = getattr(self, devrel, None)
        if not devices: 
            raise AttributeError, "%s not found on %s" % (devrel, self.id)
        devices = filter(devfilter, devices())
        for subgroup in self.children():
            devices.extend(subgroup.getSubDevices(devfilter))
        return devices


    def getAllCounts(self, devrel="devices"):
        """Count all devices within a device group and get the
        ping and snmp counts as well"""
        counts = [
            self.devices.countObjects(),
            self._status("Ping", devrel),
            self._status("Snmp", devrel),
        ]
        for group in self.children():
            sc = group.getAllCounts()
            for i in range(3): counts[i] += sc[i]
        return counts


    def countDevices(self, devrel="devices"):
        """count all devices with in a device group"""
        count = self.devices.countObjects()
        for group in self.children():
            count += group.countDevices()
        return count


    def pingStatus(self, devrel="devices"):
        """aggrigate ping status for all devices in this group and below"""
        status = self._status("Ping", devrel)
        for group in self.children():
            status += group.pingStatus()
        return status

    
    def snmpStatus(self, devrel="devices"):
        """aggrigate snmp status for all devices in this group and below"""
        status = self._status("Snmp", devrel)
        for group in self.children():
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
            "%s like '.*%s.*'" % (omniField, self.getOrganizerName()))
        return self.viewEvents(self.REQUEST)


    def getDeviceGroupOmnibusHistoryEvents(self, omniField):
        """get the history event list of this object"""
        self.REQUEST.set('ev_whereclause', 
            "%s like '%%%s%%'" % (omniField, self.getOrganizerName()))
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
             
