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
log = logging.getLogger('zubdmd')

from Products.ZenPackAdapter.db import get_db

log.info("Loading database")
_db = get_db()
_db.load()

def get(device=None, component=None):
    return _db.get_zobject(device=device, component=component)
find = get

def impacted(zobject):
    print "Local (impactFromDimensions):"
    for d in [_dimensions(x) for x in zobject.impactFromDimensions]:
        print "  * %s" % get(device=d['device'], component=d['component'])

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
    for d in [_dimensions(x) for x in zobject.impactToDimensions]:
        lobj = get(device=d['device'], component=d['component'])
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
