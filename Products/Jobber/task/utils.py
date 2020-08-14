##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import inspect

from ..zenjobs import app


def requires(*features):
    """Return a custom Task deriving from the given features.

    The method resolution order of the created custom task class is
    (*features, ZenTask, celery.app.task.Task, object) where 'features'
    are the classes given to this function.
    """
    bases = tuple(features) + (app.Task, object)
    culled = []
    for feature in reversed(bases):
        for cls in reversed(inspect.getmro(feature)):
            if cls not in culled:
                culled.insert(0, cls)
    name = ''.join(t.__name__ for t in features) + "Task"
    basetask = type(name, tuple(culled), {"abstract": True})
    return basetask
