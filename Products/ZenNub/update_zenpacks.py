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
# zenpacks into the yaml files that zennub is run from.  It should be run
# whenever zenpacks are added, removed, or upgrades.  Note that error
# handling isn't great.


import logging
import site
import sys
import yaml

import Globals
from Products.ZenNub.utils.zenpack import *
from Products.ZenNub.config.deviceclasses import ZENPACK_DEVICECLASS_YAML
from Products.ZenNub.config.modelerplugins import MODELER_PLUGIN_YAML
from Products.ZenNub.config.classmodels import CLASS_MODEL_YAML
from Products.ZenUtils.Utils import importClass

# This file contains a list of all the ZPL yaml files in each zenpack, along
# with any other metadata that is expensive to obtain.
ZENPACK_YAML_INDEX = "/opt/zenoss/etc/nub/system/zenpack_index.yaml"

logging.basicConfig(level=logging.ERROR)

noalias_dumper = yaml.dumper.Dumper
noalias_dumper.ignore_aliases = lambda self, data: True


def update_zenpack_yaml_index():
    # This loads each zenpack via ZPL and notes what yaml files it reads.
    # this is meant to be run under specific sitations (zenpacks not already
    # loaded), and it patches ZPL such as to break it.  So this should only be
    # run in its own process.
    #
    # python -c "import Globals; from Products.ZenNub.zenpack import *; update_zenpack_yaml_index();"

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
                zenpack_yaml_index[zenpack] = [x for x in yaml_list if zenpack in x]

    yaml.dump(zenpack_yaml_index, file(ZENPACK_YAML_INDEX, 'w'), default_flow_style=False, Dumper=noalias_dumper)
    print "Updated %s" % ZENPACK_YAML_INDEX


def update_system_deviceclasses_yaml():
    from ZenPacks.zenoss.ZenPackLib import zenpacklib

    # Using the information cached by update_zenpack_yaml_index,
    # Loop over all zenpacks and extract the information we need from it, then
    # write it out in a simpler yaml format.
    device_classes = {}

    try:
        zenpack_yaml_index = yaml.load(file(ZENPACK_YAML_INDEX, 'r'))
    except Exception, e:
        print "Error loading %s: %s  (try update_zenpack_yaml_index?)" % (ZENPACK_YAML_INDEX, e)

    for zenpack in zenpack_names():
        yamlfiles = zenpack_yaml_index.get(zenpack, [])
        if yamlfiles:
            print "Loading %d yaml files from %s" % (len(yamlfiles), zenpack)
            CFG = zenpacklib.load_yaml(yamlfiles)

            for dcname, dcspec in CFG.device_classes.iteritems():
                dcout = device_classes.setdefault(dcname, {})
                dcout.setdefault('zProperties', {})
                dcout.setdefault('rrdTemplates', {})

                for k, v in dcspec.zProperties.iteritems():
                    device_classes[dcname]['zProperties'][k] = v

                for tname, template in dcspec.templates.iteritems():
                    dcout['rrdTemplates'].setdefault(tname, {})
                    tout = dcout['rrdTemplates'][tname]
                    # tout.setdefault('thresholds', {})
                    tout.setdefault('datasources', {})
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
                        dsout['component'] = datasource.component
                        # dsout['eventClass'] = datasource.eventClass
                        # dsout['eventKey'] = datasource.eventKey
                        # dsout['severity'] = datasource.severity
                        dsout['commandTemplate'] = datasource.commandTemplate
                        dsout['sourcetype'] = getattr(datasource, "sourcetype", None)

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

        elif zenpack_has_directory(zenpack, 'objects'):
            xmlfiles = [x for x in zenpack_listdir(zenpack, 'objects') if x.endswith(".xml")]
            print "Loading %d XML files from %s" % (len(xmlfiles), zenpack)
        else:
            print "Zenpack %s has no YAML or XML" % zenpack


    yaml.dump(device_classes, file(ZENPACK_DEVICECLASS_YAML, 'w'), default_flow_style=False, Dumper=noalias_dumper)
    print "Updated %s" % ZENPACK_DEVICECLASS_YAML


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
        packs.append(_zenpack(moduleName=zenpack, modulePath="/opt/zenoss/ZenPacks/%s" + zenpack))

    modeler_deviceProperties = {}
    from Products.DataCollector.Plugins import ModelingManager
    loaders = ModelingManager.getInstance().getPluginLoaders(packs)
    for loader in loaders:
        plugin = loader.create()
        modeler_deviceProperties[loader.pluginName] = {
            'deviceProperties': sorted(list(set(plugin.deviceProperties))),
            'pluginLoader': loader
        }

    yaml.dump(modeler_deviceProperties, file(MODELER_PLUGIN_YAML, 'w'), default_flow_style=False, Dumper=noalias_dumper)
    print "Updated %s" % MODELER_PLUGIN_YAML

def update_classmodel_yaml():
    # this yaml file stores any relevant info about the model.  For now,
    # it's just class -> meta_type, but we could store relationship schema
    # and labels here too.

    model = {}
    from Products.ZenModel.ZenModelRM import ZenModelRM
    for zenpack in zenpack_names():
        __import__(zenpack)

    def all_subclasses(cls):
        return set(cls.__subclasses__()).union(
            [s for c in cls.__subclasses__() for s in all_subclasses(c)])
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

        model[cls.__module__] = {
            "meta_type": cls.meta_type,
            "class_label": getattr(cls, "class_label", None),
            "default_rrd_template_name": default_rrd_template_name
        }

    yaml.dump(model, file(CLASS_MODEL_YAML, 'w'), default_flow_style=False, Dumper=noalias_dumper)
    print "Updated %s" % CLASS_MODEL_YAML



if __name__ == '__main__':
    update_zenpack_yaml_index()
    update_system_deviceclasses_yaml()
    update_modeler_yaml()
    update_classmodel_yaml()

