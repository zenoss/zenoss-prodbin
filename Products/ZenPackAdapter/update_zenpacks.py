#! /usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

# This script is designed to be run standalone, and import data from the
# zenpacks into the yaml files that zminihub is run from.  It should be run
# whenever zenpacks are added, removed, or upgrades.  Note that error
# handling isn't great.


import logging
import os.path
import site
import sys
import yaml
import xml.etree.ElementTree as ET

import Globals

from Products.ZenPackAdapter.utils.zenpack import *
from Products.ZenPackAdapter.yamlconfig import (
    DEVICECLASS_YAML,
    MONITORINGTEMPLATE_YAML,
    MODELER_PLUGIN_YAML,
    PARSER_PLUGIN_YAML,
    CLASS_MODEL_YAML,
    DATASOURCE_YAML
)

from Products.ZenUtils.Utils import importClass
from DateTime import DateTime

from Products.ZenModel.RRDDataSource import RRDDataSource

# This file is used as a cache, and contains a list of all the ZPL yaml files
# in each zenpack, along with any other metadata that is expensive to obtain.
ZENPACK_YAML_INDEX = "/tmp/zenpack_index.yaml"

logging.basicConfig(level=logging.ERROR)
log = logging.getLogger('zen.zenpackadapter.update_zenpacks')

noalias_dumper = yaml.dumper.Dumper
noalias_dumper.ignore_aliases = lambda self, data: True


def all_subclasses(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)])


def update_zenpack_yaml_index():
    # This loads each zenpack via ZPL and notes what yaml files it reads.
    # this is meant to be run under specific sitations (zenpacks not already
    # loaded), and it patches ZPL such as to break it.  So this should only be
    # run in its own process.
    #
    # python -c "import Globals; from Products.ZenPackAdapter.zenpack import *; update_zenpack_yaml_index();"

    try:
        zenpack_yaml_index = yaml.load(file(ZENPACK_YAML_INDEX, 'r'))
    except IOError:
        zenpack_yaml_index = {}

    import ZenPacks.zenoss.ZenPackLib.lib.helpers.utils as zpl
    orig_load_yaml = zpl.load_yaml

    for zenpack in zenpack_names():
        if zenpack not in zenpack_yaml_index:
            yaml_list = []
            def load_yaml(yaml_doc=None, **kwargs):
                if yaml_doc is None:
                    # Load all of the yaml files in the top level directory
                    yaml_list.extend([x for x in zenpack_listdir(zenpack, '.') if x.endswith(".yaml")])
                else:
                    if isinstance(yaml_doc, list):
                        yaml_list.extend(yaml_doc)
                    else:
                        yaml_list.append(yaml_doc)

                zpl.load_yaml = orig_load_yaml
                return orig_load_yaml(yaml_doc, **kwargs)

            zpl.load_yaml = load_yaml
            try:
                if zenpack in sys.modules:
                    reload(sys.modules[zenpack])

                __import__(zenpack)
            except Exception, e:
                print "Exception on %s: %s" % (zenpack, e)
            finally:
                zpl.load_yaml = orig_load_yaml

            if zenpack not in zenpack_yaml_index:
                zenpack_yaml_index[zenpack] = sorted(list(set([x for x in yaml_list if zenpack in x])))

    yaml.dump(zenpack_yaml_index, file(ZENPACK_YAML_INDEX, 'w'), default_flow_style=False, Dumper=noalias_dumper)
    print "Updated %s" % ZENPACK_YAML_INDEX


def update_system_deviceclasses_yaml():
    from ZenPacks.zenoss.ZenPackLib import zenpacklib

    # Using the information cached by update_zenpack_yaml_index,
    # Loop over all zenpacks and extract the information we need from it, then
    # write it out in a simpler yaml format.
    device_classes = {}
    monitoring_templates = {}

    xmlfiles = ['/opt/zenoss/Products/ZenModel/data/devices.xml']
    print "Loading %d XML files from platform" % (len(xmlfiles))
    read_xmlfiles(device_classes, monitoring_templates, xmlfiles)

    try:
        zenpack_yaml_index = yaml.load(file(ZENPACK_YAML_INDEX, 'r'))
    except Exception, e:
        print "Error loading %s: %s  (try update_zenpack_yaml_index?)" % (ZENPACK_YAML_INDEX, e)
        return

    for zenpack in zenpack_names():
        yamlfiles = zenpack_yaml_index.get(zenpack, [])
        if yamlfiles:
            print "Loading %d yaml files from %s" % (len(yamlfiles), zenpack)
            CFG = zenpacklib.load_yaml(yamlfiles)

            for dcname, dcspec in CFG.device_classes.iteritems():
                dcout = device_classes.setdefault(dcname, {})
                mt_dcout = monitoring_templates.setdefault(dcname, {})
                dcout.setdefault('zProperties', {})
                mt_dcout.setdefault('rrdTemplates', {})

                for k, v in dcspec.zProperties.iteritems():
                    device_classes[dcname]['zProperties'][k] = v

                for tname, template in dcspec.templates.iteritems():
                    mt_dcout['rrdTemplates'].setdefault(tname, {})
                    tout = mt_dcout['rrdTemplates'][tname]
                    # tout.setdefault('thresholds', {})
                    tout.setdefault('datasources', {})
                    tout['id'] = tname
                    tout['targetPythonClass'] = template.targetPythonClass

                    # no need for thresholds at the moment, since we don't have
                    # events.
                    # for thname, threshold in template.thresholds.iteritems():
                    #     tout['thresholds'].setdefault(tname, {})
                    #     thout = tout['thresholds'][tname]
                    #     thout['dsnames'] = threshold.dsnames
                    #     thout['eventClass'] = threshold.eventClass
                    #     thout['severity'] = threshold.severity
                    #     thout['enabled'] = threshold.enabled
                    #     thout['type'] = threshold.type_
                    #     thout['optional'] = threshold.optional
                    #     if threshold.extra_params:
                    #         for k, v in threshold.extra_params.iteritems():
                    #             tout[k] = v

                    for dsname, datasource in template.datasources.iteritems():
                        if not datasource.enabled:
                            continue

                        tout['datasources'].setdefault(dsname, {})
                        dsout = tout['datasources'][dsname]
                        dsout['id'] = dsname
                        dsout['component'] = datasource.component
                        # dsout['eventClass'] = datasource.eventClass
                        # dsout['eventKey'] = datasource.eventKey
                        # dsout['severity'] = datasource.severity
                        dsout['commandTemplate'] = datasource.commandTemplate
                        dsout['sourcetype'] = getattr(datasource, "sourcetype", None)
                        dsout['cycletime'] = getattr(datasource, "cycletime", "${here/zCommandCollectionInterval}")

                        if datasource.extra_params:
                            for k, v in datasource.extra_params.iteritems():
                                dsout[k] = v
                        dsout['datapoints'] = {}

                        for dpname, datapoint in datasource.datapoints.iteritems():
                            dsout['datapoints'].setdefault(dpname, {})
                            dpout = dsout['datapoints'][dpname]
                            dpout['rrdtype'] = datapoint.rrdtype
                            dpout['createCmd'] = datapoint.createCmd
                            dpout['isrow'] = datapoint.isrow
                            dpout['rrdmin'] = datapoint.rrdmin
                            dpout['rrdmax'] = datapoint.rrdmax
                            dpout['description'] = datapoint.description
                            dpout['aliases'] = datapoint.aliases
                            if datapoint.extra_params:
                                for k, v in datapoint.extra_params.iteritems():
                                    dpout[k] = v

        if zenpack_has_directory(zenpack, 'objects'):
            objectdir = os.path.join(zenpack_directory(zenpack), 'objects')
            xmlfiles = []
            for dirname, _, filenames in os.walk(objectdir):
                for filename in [x for x in filenames if x.endswith('.xml')]:
                    xmlfiles.append(os.path.join(dirname, filename))

            print "Loading %d XML files from %s" % (len(xmlfiles), zenpack)
            read_xmlfiles(device_classes, monitoring_templates, xmlfiles)

    # Load zproperty default values from zenpacks.
    print "Loading zProperty defaults from ZenPacks.."
    for zenpack in zenpack_names():
        try:
            cls = importClass(zenpack, "ZenPack")
            for prop, definition in cls.getZProperties().iteritems():
                default = definition['defaultValue']
                device_classes['/']['zProperties'].setdefault(prop, default)
        except ImportError:
            print "  (unable to load ZenPack class from %s)" % zenpack

    yaml.dump(device_classes, file(DEVICECLASS_YAML, 'w'), default_flow_style=False, Dumper=noalias_dumper)
    print "Updated %s" % DEVICECLASS_YAML
    yaml.dump(monitoring_templates, file(MONITORINGTEMPLATE_YAML, 'w'), default_flow_style=False, Dumper=noalias_dumper)
    print "Updated %s" % MONITORINGTEMPLATE_YAML


def read_xmlfiles(device_classes, monitoring_templates, xmlfiles):
    xmldata = {}
    for xmlfile in xmlfiles:
        print "  reading %s" % xmlfile
        read_xml(xmlfile, xmldata)

    for dc_id in [x for x in xmldata if xmldata[x]['class'] == 'DeviceClass']:
        dcname = dc_id.replace('/zport/dmd/Devices', '')
        if dcname == '':
            dcname = '/'

        dcout = device_classes.setdefault(dcname, {})
        mt_dcout = monitoring_templates.setdefault(dcname, {})
        dcout.setdefault('zProperties', {})
        mt_dcout.setdefault('rrdTemplates', {})

        for k, v in xmldata[dc_id]['properties'].iteritems():
            if k.startswith('z'):
                device_classes[dcname]['zProperties'][k] = v

        for obj_id in xmldata:
            if not obj_id.startswith(dc_id + '/rrdTemplates/'):
                continue
            template = xmldata[obj_id]
            template_id = obj_id
            tname = obj_id.replace(dc_id + '/rrdTemplates/', '')
            if '/' in tname:
                # oops, it's a sub-object. (datasource, datapoint, etc)
                continue

            mt_dcout['rrdTemplates'].setdefault(tname, {})
            tout = mt_dcout['rrdTemplates'][tname]
            # tout.setdefault('thresholds', {})
            tout.setdefault('datasources', {})
            tout['id'] = tname
            tout['targetPythonClass'] = template['properties'].get('targetPythonClass')

            for obj_id in xmldata:
                if not obj_id.startswith(template_id + '/datasources/'):
                    continue

                ds = xmldata[obj_id]
                ds_id = obj_id
                dsname = obj_id.replace(template_id + '/datasources/', '')
                if '/' in dsname:
                    # oops, it's a sub-object. (datapoint, etc)
                    continue

                if str(ds['properties']['enabled']) != 'True':
                    continue

                # set default values, which are omitted from the XML
                dummy = importClass(ds['module'], ds['class'])("dummy")
                for propname in [x['id'] for x in dummy._properties]:
                    if propname not in ds['properties']:
                        ds['properties'][propname] = getattr(dummy, propname)

                tout['datasources'].setdefault(dsname, {})
                dsout = tout['datasources'][dsname]
                dsout['id'] = dsname
                dsout['component'] = ds['properties'].get('component')
                dsout['commandTemplate'] = ds['properties'].get('commandTemplate')
                dsout['sourcetype'] = ds['properties'].get("sourcetype", None)
                dsout['cycletime'] = ds['properties'].get("cycletime", "${here/zCommandCollectionInterval}")

                for k, v in ds['properties'].iteritems():
                    if k not in ('enabled' 'sourcetype', 'component', 'eventClass', 'severity', 'cycletime'):
                        dsout[k] = v

                dsout['datapoints'] = {}
                for obj_id in xmldata:
                    if not obj_id.startswith(ds_id + '/datapoints/'):
                        continue

                    dp = xmldata[obj_id]
                    dp_id = obj_id
                    dpname = obj_id.replace(ds_id + '/datapoints/', '')
                    if '/' in dpname:
                        # oops, it's a sub-object.
                        continue

                    dsout['datapoints'].setdefault(dpname, {})
                    dpout = dsout['datapoints'][dpname]
                    dpout['rrdtype'] = dp['properties'].get('rrdtype')
                    dpout['createCmd'] = dp['properties'].get('createCmd')
                    dpout['isrow'] = dp['properties'].get('isrow')
                    dpout['rrdmin'] = dp['properties'].get('rrdmin')
                    dpout['rrdmax'] = dp['properties'].get('rrdmax')
                    dpout['description'] = dp['properties'].get('description')
                    dpout['aliases'] = dp['properties'].get('aliases')

                    for k, v in dp['properties'].iteritems():
                        if k not in ('rrdtype', 'createCmd', 'isrow', 'rrdmin', 'rrdmax', 'description', 'aliases'):
                            dpout[k] = v


def read_xml(filename, data):
    tree = ET.parse(filename)
    root = tree.getroot()

    def _process_object(obj, prefix=""):
        obj_id = prefix + obj.get('id')
        data[obj_id] = {
            'id': obj.get('id'),
            'module': obj.get('module'),
            'class': obj.get('class'),
            'properties': {}
        }

        for property in obj.findall('property'):
            value = property.text.strip()
            try:
                value = str(value)
            except UnicodeEncodeError:
                log.warn("UnicodeEncodeError in '%s' while processing object %s", value, obj_id)

            ptype = property.get('type')

            if ptype == 'date':
                try:
                    value = float(value)
                except ValueError:
                    pass
                value = DateTime(value)
            elif ptype not in ('selection', 'string', 'text', 'password'):
                try:
                    value = eval(value)
                except NameError:
                    log.warn("Error trying to evaluate %s while processing object %s", value, obj_id)
                except SyntaxError:
                    log.debug("Non-fatal SyntaxError while trying to evaluate %s while processing object %s", value, obj_id)

            data[obj_id]['properties'][property.get('id')] = value
        for childrel in obj.findall('tomanycont'):
            prefix = obj_id + "/" + childrel.get('id') + "/"
            for childobj in childrel.findall('object'):
                _process_object(childobj, prefix=prefix)
        for childobj in obj.findall('object'):
            prefix = obj_id + "/"
            _process_object(childobj, prefix=prefix)

    for obj in root.findall('object'):
        _process_object(obj)

    return data

def update_modeler_yaml():
    # I found that I needed to load these first due to conflicts with 'zenoss'
    # namespaces in zenpacks.  There's probably a better way.
    site.addsitedir('/opt/zenoss/modelindex')
    import zenoss.protocols.services
    import zenoss.modelindex

    # Mock up enough of a zenpack object to make the plugin loader happy.
    class _zenpack(object):
        def __init__(self, moduleName, modulePath):
            self._moduleName = moduleName
            self._modulePath = modulePath
        def moduleName(self):
            return self._moduleName
        def path(self, *parts):
            return os.path.join(self._modulePath, *[p.strip('/') for p in parts])

    packs = []
    for zenpack in zenpack_names():
        packs.append(_zenpack(moduleName=zenpack, modulePath=zenpack_directory(zenpack)))

    modeler_data = {}
    from Products.DataCollector.Plugins import ModelingManager
    loaders = ModelingManager.getInstance().getPluginLoaders(packs)
    for loader in loaders:
        try:
            plugin = loader.create()
            modeler_data[loader.modPath] = {
                'pluginName': loader.pluginName,
                'modPath': loader.modPath,
                'deviceProperties': sorted(list(set(plugin.deviceProperties))),
                'pluginLoader': loader
            }
        except Exception, e:
            print e

    yaml.dump(modeler_data, file(MODELER_PLUGIN_YAML, 'w'), default_flow_style=False, Dumper=noalias_dumper)
    print "Updated %s" % MODELER_PLUGIN_YAML


def update_parser_yaml():
    # I found that I needed to load these first due to conflicts with 'zenoss'
    # namespaces in zenpacks.  There's probably a better way.
    site.addsitedir('/opt/zenoss/modelindex')
    import zenoss.protocols.services
    import zenoss.modelindex

    # Mock up enough of a zenpack object to make the plugin loader happy.
    class _zenpack(object):
        def __init__(self, moduleName, modulePath):
            self._moduleName = moduleName
            self._modulePath = modulePath

        def moduleName(self):
            return self._moduleName

        def path(self, *parts):
            return os.path.join(self._modulePath, *[p.strip('/') for p in parts])

    packs = []
    for zenpack in zenpack_names():
        packs.append(_zenpack(moduleName=zenpack, modulePath=zenpack_directory(zenpack)))

    parser_data = {}
    from Products.DataCollector.Plugins import MonitoringManager
    loaders = MonitoringManager.getInstance().getPluginLoaders(packs)
    for loader in loaders:
        try:
            loader.create()
            parser_data[loader.modPath] = {
                'pluginName': loader.pluginName,
                'modPath': loader.modPath,
                'pluginLoader': loader
            }
        except Exception, e:
            print e

    yaml.dump(parser_data, file(PARSER_PLUGIN_YAML, 'w'), default_flow_style=False, Dumper=noalias_dumper)
    print "Updated %s" % PARSER_PLUGIN_YAML


def update_classmodel_yaml():
    # this yaml file stores any relevant info about the model.  For now,
    # it's just class -> meta_type, and labels, but we could store relationship
    # schema here too.

    model = {}
    from Products.ZenModel.ZenModelRM import ZenModelRM

    for zenpack in zenpack_names():
        __import__(zenpack)

        # While loading the zenpack will pull in all the ZPL defined classes,
        # for non-zpl ones, we need to load the explicitly to find them.
        # So, brute force it is, then.
        for f in zenpack_listdir(zenpack, '.'):
            f = os.path.basename(f)
            if f.endswith(".py") and f[0].isupper():
                module = "%s.%s" % (zenpack, f[0:-3])
                try:
                    __import__(module)
                except Exception:
                    pass

    for cls in all_subclasses(ZenModelRM):
        if cls.__module__.endswith(".schema"):
            # ignore intermediate ZPL classes
            continue

        default_rrd_template_name = cls.meta_type
        if hasattr(cls, "class_label"):
            default_rrd_template_name = cls.class_label

        try:
            default_rrd_template_name = cls("dummy").getRRDTemplateName()
        except Exception:
            pass

        try:
            default_rrd_template_name = cls("dummy")._templates[-1]
        except Exception:
            pass

        model[cls.__module__] = {
            "meta_type": cls.meta_type,
            "class_label": getattr(cls, "class_label", None),
            "default_rrd_template_name": default_rrd_template_name
        }

    yaml.dump(model, file(CLASS_MODEL_YAML, 'w'), default_flow_style=False, Dumper=noalias_dumper)
    print "Updated %s" % CLASS_MODEL_YAML


def update_datasource_yaml():
    print "Scanning zenpacks for custom datasources"

    for zenpack in zenpack_names():
        if not zenpack_has_directory(zenpack, "datasources"):
            continue

        zp_dir = zenpack_directory(zenpack)
        datasource_dir = zenpack_directory(zenpack) + "/datasources"

        for path, dirs, files in os.walk(datasource_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if not f.startswith('.') and f.endswith('.py'):
                    subPath = path[len(zp_dir):]
                    parts = subPath.strip('/').split('/')
                    parts.append(f[:f.rfind('.')])
                    modName = '.'.join([zenpack] + parts)
                    importClass(modName)

    data = {}
    for cls in all_subclasses(RRDDataSource):
        for sourcetype in cls.sourcetypes:

            modname = cls.__module__
            if modname.endswith(".__init__"):
                modname = modname[0:0 - len(".__init__")]
            data[sourcetype] = {
                "modulename": modname,
                "classname": cls.__name__
            }

    yaml.dump(data, file(DATASOURCE_YAML, 'w'), default_flow_style=False, Dumper=noalias_dumper)
    print "Updated %s" % DATASOURCE_YAML


if __name__ == '__main__':
    try:
        import ZenPacks.zenoss.ZenPackLib
    except ImportError:
        log.error("ZenPackLib is not currently installed.  Unable to continue with update_zenpacks.py.")
        sys.exit(0)

    update_zenpack_yaml_index()
    update_system_deviceclasses_yaml()
    update_modeler_yaml()
    update_parser_yaml()
    update_classmodel_yaml()
    update_datasource_yaml()

