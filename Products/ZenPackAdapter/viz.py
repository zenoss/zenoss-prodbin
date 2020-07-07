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
from graphviz import Digraph
import site

logging.basicConfig()
log = logging.getLogger('viz')

from .db import SNAPSHOT_DIR

def viz(deviceId):
    filename = "%s/%s.pickle" % (SNAPSHOT_DIR, deviceId)
    if os.path.exists(filename):
        log.debug("Reading DataMapper for device %s from last snapshot.", id)
        with open(filename, "r") as f:
            mapper = pickle.load(f)
    else:
        log.error("No snapshot found for %s" % deviceId)


    dot = Digraph(comment="Device '%s'" % deviceId)
    for object_id in mapper.objects:
        datum = mapper.get(object_id)
        tooltip = datum["type"] + "\n"
        for k, v in datum["properties"].iteritems():
            tooltip += "  %s: %s\n" % (k, v)

        dot.node(object_id, datum["title"], tooltip=tooltip, fontsize="8")

    for object_id in mapper.objects:
        datum = mapper.get(object_id)

        for link_name, remote_ids in datum["links"].iteritems():
            for remote_id in remote_ids:
                dot.edge(object_id, remote_id, label=link_name, fontsize="8")

    return dot
