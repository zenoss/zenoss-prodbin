##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from .utils import all_parent_dcs

class Device(object):
    def __init__(self, deviceId=None, title=None, manageIp=None, device_class=None, zProperties=None):
        if deviceId is None:
            raise ValueError("Device.device_class is required")

        if device_class is None:
            raise ValueError("Device.device_class is required")

        if manageIp is None:
            raise ValueError("Device.manageIp is required")

        if zProperties is None:
            zProperties = {}

        self.deviceId = deviceId
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
            if zProp in self.db.device_classes[dc].zProperties:
                return True

        return False

    def getProperty(self, zProp):
        if zProp in self.zProperties:
            return self.zProperties[zProp]

        for dc in all_parent_dcs(self.device_class):
            if zProp in self.db.device_classes[dc].zProperties:
                return self.db.device_classes[dc].zProperties[zProp]

    def getMonitoredComponents(self, collector=None):
        mapper = self.db.get_mapper(self.deviceId)
        for object_id, obj in mapper.all():
            if mapper.get_object_type(object_id).device:
                continue

            # should filter based on monitored status, but we don't have
            # such a thing.  So just return all components.
            yield obj

    # def getRRDTemplates(self):
    #     """
    #     Returns all the templates bound to this Device

    #     @rtype: list

    #     """
    #     if not self.hasProperty('zDeviceTemplates'):
    #         default = self.getRRDTemplateByName(self.getRRDTemplateName())
    #         if not default:
    #             return []
    #         return [default]

    #     result = []
    #     for name in self.getProperty('zDeviceTemplates'):
    #         template = self.getRRDTemplateByName(name)
    #         if template:
    #             result.append(template)
    #     return result

    # def getRRDTemplateName(self):
    #     """Return the target type name of this component.  By default meta_type.
    #     Override to create custom type selection.
    #     """
    #     clsname =
    #     return self.db.classmodel[clsname]["meta_type"]

    # def getRRDTemplates(self):
    #     default = self.getRRDTemplateByName(self.getRRDTemplateName())
    #     if not default:
    #         return []
    #     return [default]

    # def getRRDTemplate(self):
    #     try:
    #         return self.getRRDTemplates()[0]
    #     except IndexError:
    #         return None

    # def getRRDTemplateByName(self, name):
    #     "Return the template of the given name."
    #     try:
    #         return self._getOb(name)
    #     except AttributeError:
    #         pass
    #     for obj in aq_chain(self):
    #         try:
    #             return obj.rrdTemplates._getOb(name)
    #         except AttributeError:
    #             pass
    #     return None




class ModelerPlugin(object):
    def __init__(self, pluginId=None, deviceProperties=None, pluginLoader=None):
        if deviceProperties is None:
            deviceProperties = []

        self.pluginId = pluginId
        self.deviceProperties = deviceProperties

        # the only reason we store the pluginLoader is that the current
        # zenmodeler wants to be handed loader objects, not just plugin names.
        # This could be changed.
        self.pluginLoader = pluginLoader

class DeviceClass(object):
    def __init__(self, deviceClassId=None, zProperties=None, rrdTemplates=None):
        if zProperties is None:
            zProperties = {}
        if rrdTemplates is None:
            rrdTemplates = {}

        self.deviceClassId = deviceClassId
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
    def __init__(self, datasources=None, targetPythonClass=None):
        self.datasources = {}
        if datasources is None:
            datasources = {}

        self.targetPythonClass = targetPythonClass

        if not isinstance(datasources, dict):
            raise TypeError("datasources must be a dict")
        for dsname, dsdict in datasources.iteritems():
            self.datasources[dsname] = RRDDataSource(**dsdict)

    def getRRDDataSources(self, dsType=None):
        if dsType is None: return self.datasources

        return [ds for ds in self.datasources
                if ds.sourcetype == dsType]

class RRDDataSource(object):
    def __init__(self, component=None, commandTemplate=None, datapoints=None,
                sourcetype=None,
                 **kwargs):
        if datapoints is None:
            datapoints = {}

        self.component = component
        self.commandTemplate = commandTemplate
        self.sourcetype = sourcetype
        self.datapoints = {}

        if not isinstance(datapoints, dict):
            raise TypeError("datapoints must be a dict")
        for dpname, dpdict in datapoints.iteritems():
            self.datapoints[dpname] = RRDDataPoint(**dpdict)

        for k, v in kwargs.iteritems():
            setattr(self, k, v)

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
