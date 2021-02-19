#!/usr/bin/env python

##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import Globals

import logging
import os.path
import pickle
import sys
import site

from IPython import embed

logging.basicConfig()
log = logging.getLogger('zen.zminidmd')

from Products.ZenPackAdapter.db import get_db
from Products.ZenPackAdapter.impact import update_impact as _update_impact, update_all_impacts
from Products.ZenPackAdapter.services import ModelerService, PythonConfig

# Load zope adapters so that update_impact is possible
from OFS.Application import import_products
import_products()
from Zope2.App.zcml import load_site
load_site()

logging.getLogger('zen').setLevel(logging.INFO)

log.info("Loading database")
_db = get_db()
_db.load()

def get(device=None, component=None):
    return _db.get_zobject(device=device, component=component)
find = get

def get_configs(device=None, component=None):
    d = _db.get_zobject(device=device, component=component)
    modSvc = ModelerService()
    pycfg = PythonConfig(modSvc)
    configs = pycfg.remote_getDeviceConfig(names=[d.id])
    if len(configs) > 0:
        return configs[0]
    return None

def impacted(zobject):
    print "Local (impactFromDimensions):"
    if zobject.impactFromDimensions is None:
        print "  (none)"
    else:
        for d in [_dimensions(x) for x in zobject.impactFromDimensions]:
            print "  * %s" % get(device=d['device'], component=d.get('component', None))

    print "Remote (impactToDimensions refers to this object):"
    devId = zobject.device().id
    compId = zobject.id

    for device in _db.devices:
        for component in [x[0] for x in _db.get_mapper(device).all()]:
            robj = get(device, component)
            if not getattr(robj, 'impactToDimensions', None):
                continue
            for d in [_dimensions(x) for x in robj.impactToDimensions if isinstance(x, basestring)]:
                if d['device'] == devId and d.get('component', None) == compId:
                    print "  * %s" % robj
impacted_by = impacted


def impacts(zobject):
    print "Local (impactToDimensions):"
    if zobject.impactToDimensions is None:
        print "  (none)"
    else:
        for d in [_dimensions(x) for x in zobject.impactToDimensions]:
            lobj = get(device=d['device'], component=d.get('component', None))
            print "  * %s" % lobj

    print "Remote (impactFromDimensions refers to this object):"
    devId = zobject.device().id
    compId = zobject.id

    for device in _db.devices:
        for component in [x[0] for x in _db.get_mapper(device).all()]:
            robj = get(device, component)
            if not getattr(robj, 'impactFromDimensions', None):
                continue
            for d in [_dimensions(x) for x in robj.impactFromDimensions if isinstance(x, basestring)]:
                if d['device'] == devId and d.get('component', None) == compId:
                    print "  * %s" % robj

def update_impact(zobject):
    print "Updating impact for %s" % zobject
    _update_impact(device=zobject.device().id, component=zobject.id)
    impacts(zobject)
    impacted(zobject)

def _dimensions(s):
    d = {}
    for kvp in s.split(","):
        k, v = kvp.split("=")
        d[str(k)] = v
    return d

def cleandir(o):
    return [x for x in dir(o) if not x.startswith("_") and not x.startswith("z")]

def sync():
    _db.load()


embed()
