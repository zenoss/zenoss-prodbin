##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os

from DateTime import DateTime
from Products.ZenUtils.Utils import binPath
from Products.ZenNub.utils.tales import talesCompile, talesEvalStr

from .utils import all_parent_dcs
from .utils.zenpack import zenpack_names, zenpack_directory


class Device(object):
    def __init__(self, id=None, title=None, manageIp=None, device_class=None, zProperties=None):
        if id is None:
            raise ValueError("Device.device_class is required")

        if device_class is None:
            raise ValueError("Device.device_class is required")

        if manageIp is None:
            raise ValueError("Device.manageIp is required")

        if zProperties is None:
            zProperties = {}

        self.id = id
        self.title = title
        self.manageIp = manageIp
        self.device_class = device_class
        self.zProperties = {}

        from .db import get_nub_db
        self.db = get_nub_db()

        if not isinstance(zProperties, dict):
            raise TypeError("zProperties must be a dict")
        self.zProperties = zProperties

    def hasProperty(self, zProp):
        if zProp in self.zProperties:
            return True

        for dc in all_parent_dcs(self.device_class):
            if dc in self.db.device_classes:
                if zProp in self.db.device_classes[dc].zProperties:
                    return True

        return False

    def getProperty(self, zProp):
        if zProp in self.zProperties:
            return self.zProperties[zProp]

        for dc in all_parent_dcs(self.device_class):
            if dc in self.db.device_classes:
                if zProp in self.db.device_classes[dc].zProperties:
                    return self.db.device_classes[dc].zProperties[zProp]

    def getPropertyDefault(self, zProp):
        for dc in all_parent_dcs(self.device_class):
            if dc in self.db.device_classes:
                if zProp in self.db.device_classes[dc].zProperties:
                    return self.db.device_classes[dc].zProperties[zProp]

    def getAllProperties(self):
        props = {}
        for zProp, value in self.zProperties.iteritems():
            props.setdefault(zProp, value)

        for dc in all_parent_dcs(self.device_class):
            for zProp, value in self.db.device_classes[dc].zProperties.iteritems():
                props.setdefault(zProp, value)

        return props

    def getMonitoredComponents(self, collector=None):
        mapper = self.db.get_mapper(self.id)
        for object_id, obj in mapper.all():
            if mapper.get_object_type(object_id).device:
                continue

            # should filter based on monitored status, but we don't have
            # such a thing.  So just return all components.
            yield object_id, obj


class ModelerPlugin(object):
    def __init__(self, id=None, deviceProperties=None, pluginLoader=None, pluginName=None, modPath=None):
        if deviceProperties is None:
            deviceProperties = []

        self.id = id
        self.deviceProperties = deviceProperties
        self.pluginName = pluginName
        self.modPath = modPath

        # the only reason we store the pluginLoader is that the current
        # zenmodeler wants to be handed loader objects, not just plugin names.
        # This could be changed.
        self.pluginLoader = pluginLoader


class ParserPlugin(object):
    def __init__(self, id=None, pluginLoader=None, pluginName=None, modPath=None):
        self.id = id
        self.pluginName = pluginName
        self.modPath = modPath

        # the only reason we store the pluginLoader is that the current
        # zenmodeler wants to be handed loader objects, not just plugin names.
        # This could be changed.
        self.pluginLoader = pluginLoader


class DeviceClass(object):
    def __init__(self, id=None, zProperties=None, rrdTemplates=None):
        if zProperties is None:
            zProperties = {}
        if rrdTemplates is None:
            rrdTemplates = {}

        self.id = id
        self.rrdTemplates = {}
        self.zProperties = {}

        if not isinstance(zProperties, dict):
            raise TypeError("zProperties must be a dict")
        self.zProperties = zProperties

        if not isinstance(rrdTemplates, dict):
            raise TypeError("rrdTemplates must be a dict")
        for tname, tdict in rrdTemplates.iteritems():
            self.rrdTemplates[tname] = RRDTemplate(**tdict)


class RRDTemplate(object):
    def __init__(self, id=None, datasources=None, targetPythonClass=None):
        self.datasources = {}
        if datasources is None:
            datasources = {}

        self.id = id
        self.targetPythonClass = targetPythonClass

        if not isinstance(datasources, dict):
            raise TypeError("datasources must be a dict")
        for dsname, dsdict in datasources.iteritems():
            self.datasources[dsname] = RRDDataSource(rrdTemplate=self, **dsdict)

    def getRRDDataSources(self, dsType=None):
        if dsType is None:
            return self.datasources.values()

        return [ds for ds in self.datasources.values()
                if ds.sourcetype == dsType]


class RRDDataSource(object):
    def __init__(self, id=None, component=None, commandTemplate=None, datapoints=None,
                 cycletime=None, sourcetype=None, rrdTemplate=None,
                 **kwargs):
        if datapoints is None:
            datapoints = {}

        self.id = id
        self.component = component
        self.commandTemplate = commandTemplate
        self.sourcetype = sourcetype
        self.datapoints = {}
        self.cycletime = cycletime
        self._rrdTemplate = rrdTemplate

        if not isinstance(datapoints, dict):
            raise TypeError("datapoints must be a dict")
        for dpname, dpdict in datapoints.iteritems():
            self.datapoints[dpname] = RRDDataPoint(**dpdict)

        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def rrdTemplate(self):
        return self._rrdTemplate

    def talesEval(self, text, context):
        from Products.ZenNub.adapters import ZDevice, ZDeviceComponent

        if text is None:
            return

        if isinstance(context, Device):
            # Probably should switch over to using the adapter everywhere, but
            # for now..
            zprops = context.getAllProperties()
            extra = {
                'here': zprops,
                'device': zprops,
                'dev': zprops,
                'devname': context.id,
                'datasource': self,
                'ds': self
            }
        elif isinstance(context, ZDevice) or isinstance(context, ZDeviceComponent):
            extra = {
                'here': context,
                'device': context.device(),
                'dev': context.device(),
                'devname': context.device().id,
                'datasource': self,
                'ds': self
            }
        else:
            raise ValueError("Context must be a Device Model or ZDeviceOrComponent object")

        return talesEvalStr(str(text), {}, extra=extra)

    def getCycleTime(self, context):
        return int(self.talesEval(self.cycletime, context))

    def getCommand(self, context, cmd=None, device=None):
        """Return localized command target.
        """
        # Perform a TALES eval on the expression using self
        if cmd is None:
            cmd = self.commandTemplate
        if not cmd.startswith('string:') and not cmd.startswith('python:'):
            cmd = 'string:%s' % cmd
        talesCompile(cmd)

        zprops = device.getAllProperties()
        packs = []

        # Provide a minimal zenpackmanager->zenpack object that just has the path method.
        class _zenpack(object):
            def __init__(self, modulePath):
                self._modulePath = modulePath

            def path(self, *parts):
                return os.path.join(self._modulePath, *[p.strip('/') for p in parts])

        for zenpack in zenpack_names():
            packs.append({zenpack: _zenpack(modulePath=zenpack_directory(zenpack))})

        zprops['ZenPackManager'] = {
            'packs': packs
        }
        zprops['title'] = context.get('title')

        extra = {
            'here': zprops,
            'context': zprops,
            'device': zprops,
            'devname': device.id,
            'dev': zprops,
            'datasource': self,
            'ds': self,
            'nothing': None,
            'now': DateTime()
        }

        res = talesEvalStr(str(cmd), {}, extra=extra)

        return self.checkCommandPrefix(device, res)

    def checkCommandPrefix(self, device, cmd):
        zCommandPath = device.getProperty('zCommandPath')

        if not cmd.startswith('/') and not cmd.startswith('$'):
            if zCommandPath and not cmd.startswith(zCommandPath):
                cmd = os.path.join(zCommandPath, cmd)
            elif binPath(cmd.split(" ", 1)[0]):
                # if we get here it is because cmd is not absolute, doesn't
                # start with $, zCommandPath is not set and we found cmd in
                # one of the zenoss bin dirs
                cmdList = cmd.split(" ", 1)  # split into command and args
                cmd = binPath(cmdList[0])
                if len(cmdList) > 1:
                    cmd = "%s %s" % (cmd, cmdList[1])

        return cmd


class RRDDataPoint(object):
    def __init__(self, rrdtype=None, createCmd=None, isrow=None,
                 rrdmin=None, rrdmax=None, description=None, aliases=None,
                 **kwargs):

        self.rrdtype = rrdtype
        self.createCmd = createCmd
        self.isrow = isrow,
        self.rrdmin = rrdmin
        self.rrdmax = rrdmax
        self.description = description
        self.aliases = aliases

        for k, v in kwargs.iteritems():
            setattr(self, k, v)

class ClassModel(object):
    def __init__(self, module=None, meta_type=None, class_label=None, default_rrd_template_name=None):
        self.module = module
        self.meta_type = meta_type
        self.class_label = class_label
        self.default_rrd_template_name = default_rrd_template_name


class DataSource(object):
    def __init__(self, id=None, modulename=None, classname=None):
        self.id = id
        self.modulename = modulename
        self.classname = classname
