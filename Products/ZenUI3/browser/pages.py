##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################
import json
from Products import Zuul
from Products.Zuul.interfaces import IInfo
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ZopeTwoPageTemplateFile
from Products.Zuul.routers.device import DeviceRouter
from Products.Zuul.routers.nav import DetailNavRouter

class ITInfrastructure(BrowserView):

    __call__ = ZopeTwoPageTemplateFile("templates/itinfrastructure.pt")

    def getTrees(self):        
        router = DeviceRouter(self.context.dmd, {});
        method = router.getTree        
        settings = self.context.dmd.UserInterfaceSettings.getInterfaceSettings()
        if settings['incrementalTreeLoad']:
            method = router.asyncGetTree
        deviceTree = method('/zport/dmd/Devices')
        # system
        systemTree = method('/zport/dmd/Systems')
        # groups
        groupTree = method('/zport/dmd/Groups')        
        # location
        locTree = method('/zport/dmd/Locations')
        js =  """
             Zenoss.env.device_tree_data = %s;
             Zenoss.env.system_tree_data = %s;
             Zenoss.env.group_tree_data = %s;
             Zenoss.env.location_tree_data = %s;
        """ % (json.dumps(deviceTree),
               json.dumps(systemTree),
               json.dumps(groupTree),
               json.dumps(locTree))
        return js


class DeviceDetails(BrowserView):

    __call__ = ZopeTwoPageTemplateFile('templates/devdetail.pt')

    def getComponentTree(self):
        router = DeviceRouter(self.context.dmd, {});
        uid = self.context.getPrimaryId()        
        tree = router.getComponentTree(uid)
        js = """
            Zenoss.env.componentTree = %s;
        """ % json.dumps(tree)
        return js

    def fetchLeftHandMenu(self):
        router = DetailNavRouter(self.context.dmd, {})
        menuIds = ['More','Add','TopLevel','Manage']
        uid = self.context.getPrimaryId()
        response = router.getDetailNavConfigs(uid=uid, menuIds=menuIds)
        js = """
            Zenoss.env.lefthandnav = %s;
        """ % json.dumps(response.data)
        return js

    def getInfoObject(self):
        info = IInfo(self.context)
        # links is very expensive so do not marshal that
        keys = [key for key in dir(info)
                if not key.startswith('_') and not callable(getattr(info, key)) and key not in ('links', 'uptime', 'events', 'deviceClass') ]
        response = dict(data=Zuul.marshal(info, keys))
        js = """
            Zenoss.env.infoObject = %s;
        """ % (json.dumps(response))
        return js
