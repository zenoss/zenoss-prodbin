
import os
import time
import glob
import rrdtool
import random

import Globals
try:
    from Products.ZenRRD.plugins.plugin import *
except ImportError:
    from plugin import *

# set variables for command-line testing
locals().setdefault('REQUEST', None)
locals().setdefault('name', 'test')

title = 'Aggregate CPU Use'
label = 'CPU'
width = 500
height = 100
start='-1d'
end='now'
rpn = ''

env = locals().copy()
args = []
if REQUEST:
    REQUEST.response.setHeader('Content-type', 'image/png')
    kv = zip(REQUEST.keys(), REQUEST.values())
    env.update(dict(kv))
    for k, v in kv:
       if k == 'arg':
          args.append(v)

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

perf = os.path.join(os.environ['ZENHOME'], 'perf')
rpn = env['rpn']
rfiles = []
for d, _, fs in os.walk(perf):
    parts = []
    for f in fs:
	for n in 'Wait System User':
	    if f.find('ssCpuRaw' + n) >= 0:
	        parts.append(f)
    if len(parts) == 3:
	parts.sort()
        rfiles.append( (d, parts) )
ifiles = []
for d, _, fs in os.walk(perf):
    for f in fs:
        if f.find('cpuPercentProcessorTime') >= 0:
            ifiles.append(os.path.join(d, f))
count = len(rfiles + ifiles)

defs = []
for i, f in enumerate(rfiles):
    d, files = f
    for j, f in enumerate(files):
       defs.append('DEF:d%dx%d=%s/%s:ds0:AVERAGE' % (j, i, d, f))

for i, f in enumerate(ifiles):
    defs.append('DEF:di%d=%s:ds0:AVERAGE' % (i, f))
cdefs = []
for i, f in enumerate(rfiles):
    cdefs.append('CDEF:cr%d=d0x%d,d1x%d,+,d2x%d,+%s' % (i, i, i, i, rpn))
for i, f in enumerate(ifiles):
    cdefs.append('CDEF:ci%d=di%d%s' % (i, i, rpn))
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
open('/tmp/ttt', 'w').write(`cmd` + '\n')
rrdtool.graph(*cmd)
graph = read(fname)
