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

def getImmediateView(ob):
    if hasattr(ob, "factory_type_information"):
        return ob.factory_type_information[0]['immediate_view']
    else:
        raise NameError('Cannot find default view for "%s"' %
                        '/'.join(ob.getPhysicalPath()))

def immediate_view(ob):
    view = getImmediateView(ob)
    path = ob.getPhysicalPath() + (view,)
    return '/'.join(path)
     
def DeviceClass(ob):
    id = '.'.join(ob.getPhysicalPath())
    return '/zport/dmd/itinfrastructure#devices:' + id

def Location(ob):
    id = '.'.join(ob.getPhysicalPath())
    return '/zport/dmd/itinfrastructure#locs:' + id

def System(ob):
    id = '.'.join(ob.getPhysicalPath())
    return '/zport/dmd/itinfrastructure#systems:' + id

def DeviceGroup(ob):
    id = '.'.join(ob.getPhysicalPath())
    return '/zport/dmd/itinfrastructure#groups:' + id

def IpNetwork(ob):
    id = '.'.join(ob.getPhysicalPath())
    return '/zport/dmd/networks#networks:' + id

def DeviceComponent(ob):
    devpath = ob.device().getPrimaryUrlPath()
    return ':'.join([devpath+'/devicedetail#deviceDetailNav', ob.meta_type,
                    ob.getPrimaryUrlPath()])

def Process(ob):
    id = '.'.join(ob.getPhysicalPath())
    return '/zport/dmd/process#processTree:' + id

def Service(ob):
    id = '.'.join(ob.getPhysicalPath())
    if id.startswith('.zport.dmd.Services.WinService'):
        return '/zport/dmd/winservice#navTree:' + id
    return '/zport/dmd/ipservice#navTree:' + id

def MonitoringTemplate(ob):
    id = '/'.join(ob.getPhysicalPath())
    if id.startswith('/zport/dmd/Devices'):
        return '/zport/dmd/template#templateTree:' + id
    view = getImmediateView(ob)
    return '%s/%s' % (id, view)

def ReportClass(ob):
    id = '.'.join(ob.getPhysicalPath())
    return '/zport/dmd/reports#reporttree:' + id

