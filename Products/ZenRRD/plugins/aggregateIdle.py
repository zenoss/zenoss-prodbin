##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os
import time
import rrdtool

import Globals
try:
    from Products.ZenRRD.plugins.plugin import *
except ImportError:
    from plugin import *

title = 'Aggregate Idle Time'
label = 'Idle'
width = 500
height = 100
start='-1d'
end='now'
rpn = ''

env = locals().copy()
args = getArgs(REQUEST, env)
for k, v in env.items():
    locals()[k] = v
fname = "%s/graph-%s.png" % (TMPDIR,name)
cmd = [fname,
       '--imgformat=PNG',
       '--start=%(start)s' % env,
       '--end=%(end)s' % env,
       '--title=%(title)s' % env,
       '--height=%(height)s' % env,
       '--width=%(width)s' % env,
       '--lower-limit=0',
       '--vertical-label=%(label)s' % env] + args

from Products.ZenUtils.Utils import zenPath
perf = zenPath('perf')
rpn = env['rpn']
rfiles = []
for d, _, fs in os.walk(perf):
    for f in fs:
        if f.find('ssCpuRawIdle') >= 0:
            rfiles.append(os.path.join(d, f))
ifiles = []
for d, _, fs in os.walk(perf):
    for f in fs:
        if f.find('cpuPercentProcessorTime') >= 0:
            ifiles.append(os.path.join(d, f))
count = len(rfiles + ifiles)

defs = []
for i, f in enumerate(rfiles):
    defs.append('DEF:dr%d=%s:ds0:AVERAGE' % (i, f))
for i, f in enumerate(ifiles):
    defs.append('DEF:di%d=%s:ds0:AVERAGE' % (i, f))
cdefs = []
for i, f in enumerate(rfiles):
    cdefs.append('CDEF:cr%d=dr%d%s' % (i, i, rpn))
for i, f in enumerate(ifiles):
    cdefs.append('CDEF:ci%d=100,di%d,-%s' % (i, i, rpn))
lcdef = ['CDEF:lcdef=']
now = time.time()
for i, f in enumerate(rfiles):
    lcdef.append('TIME,%d,GT,cr%d,cr%d,UN,0,cr%d,IF,IF,' % (now, i, i, i))
for i, f in enumerate(ifiles):
    lcdef.append('TIME,%d,GT,ci%d,ci%d,UN,0,ci%d,IF,IF,' % (now, i, i, i))
lcdef.append('+,'*(len(ifiles) + len(rfiles) - 1))
if rpn:
    lcdef.append(rpn[1:])
stacks=[]
area=False
for i, f in enumerate(rfiles):
    color =  (0xf00f037 << (i % 24))
    color = '#%06x' % (color & 0xffffff)
    if not area:
        stacks.append('AREA:cr%d%s' % (i, color))
        area = True
    else:
        stacks.append('STACK:cr%d%s' % (i, color))
for i, f in enumerate(ifiles):
    color =  (0xf00f037 << (i % 24))
    color = '#%06x' % (color & 0xffffff)
    if not area:
        stacks.append('AREA:ci%d%s' % (i, color))
        area = True
    else:
        stacks.append('STACK:cr%d%s' % (i, color))
cmd.extend(defs)
cmd.extend(cdefs)
cmd.append(''.join(lcdef))
cmd.extend(stacks)
cmd.extend(['GPRINT:lcdef:LAST:Current\\:%8.2lf %s',
            'GPRINT:lcdef:AVERAGE:Average\\:%8.2lf %s',
            'GPRINT:lcdef:MAX:Maximum\\:%8.2lf %s'])
cmd = [c.strip() for c in cmd if c.strip()]
import rrdtool
graph = None
if defs:
    rrdtool.graph(*cmd)
    graph = open(fname, 'rb').read()
