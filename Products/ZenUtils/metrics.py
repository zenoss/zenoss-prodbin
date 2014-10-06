##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

def ensure_prefix(prefix, metric):
    """
    Make sure that a metric name starts with a given prefix, joined by an
    underscore. Returns the prefixed metric name.
    """
    if metric.startswith(prefix + "_"):
        return metric
    return "%s_%s" % (prefix, metric)