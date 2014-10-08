##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

SEPARATOR_CHAR = "/"


def ensure_prefix(prefix, metric):
    """
    Make sure that a metric name starts with a given prefix, joined by an
    underscore. Returns the prefixed metric name.
    """
    if metric.startswith(prefix + SEPARATOR_CHAR):
        return metric
        return "%s%s%s" % (prefix, SEPARATOR_CHAR, metric)
