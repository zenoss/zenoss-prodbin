##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import Interface

from Products.ZenUtils.GlobalConfig import globalConfToDict

_FEATURE_PREFIX = "zcml-"
_flen = len(_FEATURE_PREFIX)


class IAddGlobalFeatures(Interface):
    pass


def addGlobalFeatures(_context):
    # inject into zcml context the global features specified in global.conf
    conf = globalConfToDict()
    for key, value in conf.iteritems():
        if key[:_flen] == _FEATURE_PREFIX:
            feature = key[_flen:]

            if (
                not feature
                or not isinstance(value, basestring)
                or (value.lower() != "feature" and value.lower() != "yes")
            ):

                continue
            # add the feature to the existing global zcml context
            _context.provideFeature(unicode(feature))
