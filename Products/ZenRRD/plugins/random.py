import os
import time
import glob
import rrdtool
import random
from Products.ZenRRD.plugins.plugin import *

if REQUEST:
    REQUEST.response.setHeader('Content-type', 'image/png')
NAME='test'
DRANGE=129600
fname = "%s/graph-%s.png" % (TMPDIR,NAME)
now = time.time()
graph = cached(fname)
if not graph:
    start = now - DRANGE

    env = {}
    env.update(os.environ)
    anyOldFile = random.choice(glob.glob('%(ZENHOME)s/perf/Devices/*/*.rrd' % env))
    basename=os.path.basename(anyOldFile[:-4])
    env.update(locals())
    opts = '''
    %(fname)s
    --imgformat=PNG
    --start=%(start)d
    --end=%(now)d
    -F -E --height=100 --width=500 --vertical-label=random
    DEF:ds0=%(anyOldFile)s:ds0:AVERAGE
    CDEF:rpn0=ds0,100,/
    AREA:rpn0#00cc00:%(basename)s
    GPRINT:rpn0:LAST:cur\\:%%0.2lf
    GPRINT:rpn0:AVERAGE:avg\\:%%0.2lf
    GPRINT:rpn0:MAX:max\\:%%0.2lf\\j''' % env
    opts = opts.split()
    rrdtool.graph(*opts)
    graph = read(fname)
