##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


# It probably isn't a great example to follow style-wise.

import os
import time
import glob
import rrdtool
import random
from Products.ZenRRD.plugins.plugin import *
from Products.ZenUtils.Utils import zenPath

if REQUEST:
    REQUEST.response.setHeader('Content-type', 'image/png')
DRANGE=129600
fname = "%s/graph-%s.png" % (TMPDIR,name)
now = time.time()
graph = cached(fname, 0)                # don't cache
if not graph:
    start = now - DRANGE

    env = {}
    env.update(os.environ)
    anyOldFile = random.choice(glob.glob(zenPath('/perf/Devices/*/*.rrd')))
    basename=os.path.basename(anyOldFile[:-4])
    width=500
    height=100
    env.update(locals())
    if REQUEST:
        env.update(dict(zip(REQUEST.keys(), REQUEST.values())))
    opts = '''
    %(fname)s
    --imgformat=PNG
    --start=%(start)d
    --end=%(now)d
    -F -E --height=%(height)s --width=%(width)s --vertical-label=random
    DEF:ds0=%(anyOldFile)s:ds0:AVERAGE
    CDEF:rpn0=ds0,100,/
    AREA:rpn0#CC00CC:%(basename)s
    GPRINT:rpn0:LAST:cur\\:%%0.2lf
    GPRINT:rpn0:AVERAGE:avg\\:%%0.2lf
    GPRINT:rpn0:MAX:max\\:%%0.2lf\\j''' % env
    opts = opts.split()
    rrdtool.graph(*opts)
    graph = read(fname)
