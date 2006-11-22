import os
import time
import glob
import rrdtool
import random
try:
    import Globals
    from Products.ZenRRD.plugins.plugin import *
except ImportError:
    from plugin import *

# set variables for command-line testing
locals().setdefault('REQUEST', None)
locals().setdefault('name', 'test')

title = 'Area Line Graph'
label = ''
width = 500
height = 100
devices = '.*'
area = 'ifInOctets'
line = 'ifOutOctets'
areaLabel = 'In'
lineLabel = 'Out'
start='-7d'
end='now'
rpn = ''

import re

env = locals().copy()
args = getArgs(REQUEST, env)
fname = "%s/graph-%s.png" % (TMPDIR,name)
for k, v in env.items():
    locals()[k] = v
afiles = []
lfiles = []
perf = os.path.join(os.environ['ZENHOME'], 'perf')
devPat = re.compile('.*%s.*' % devices)
for d, _, fs in os.walk(perf):
    if devPat.match(d):
        for f in fs:
            if f.find(area) >= 0:
                afiles.append(os.path.join(d, f))
            if f.find(line) >= 0:
                lfiles.append(os.path.join(d, f))
files = afiles + lfiles
acount = len(afiles)
count = len(files)

defs = []
for i, f in enumerate(files):
    defs.append('DEF:d%d=%s:ds0:AVERAGE' % (i, f))
cdefs = []
for i in range(count):
    cdefs.append('CDEF:c%d=d%d%s' % (i, i, rpn))
lcdef1 = ['CDEF:lcdef1=']
for i in range(acount):
    lcdef1.append('TIME,%d,GT,d%d,d%d,UN,0,d%d,IF,IF,' % (now, i, i, i))
lcdef1.append('+,'*(acount-1))
if rpn:
    lcdef1.append(rpn[1:])
lcdef1 = ''.join(lcdef1)
lcdef2 = ['CDEF:lcdef2=']
for i in range(acount, count):
    lcdef2.append('TIME,%d,GT,d%d,d%d,UN,0,d%d,IF,IF,' % (now, i, i, i))
lcdef2.append('+,'*(count-acount-1))
if rpn:
    lcdef2.append(rpn[1:])
lcdef2 = ''.join(lcdef2)
stacks=[]
lcolor = len(colors)
for i in range(acount):
    stacks.append('AREA:c%d#%s::STACK' % (i, colors[i % lcolor]))
for i in range(acount, count):
    stacks.append('LINE:c%d#%s::STACK' % (i, colors[i % lcolor]))
cmd = [fname] + basicArgs(env) + args + defs + cdefs + [lcdef1, lcdef2] + stacks 
cmd.extend(['GPRINT:lcdef1:LAST:%s Current\\:%%8.2lf %%s' % areaLabel,
            'GPRINT:lcdef1:AVERAGE:Average\\:%8.2lf %s',
            'GPRINT:lcdef1:MAX:Maximum\\:%8.2lf %s\\n'])
cmd.extend(['GPRINT:lcdef2:LAST:%s Current\\:%%8.2lf %%s' % lineLabel,
            'GPRINT:lcdef2:AVERAGE:Average\\:%8.2lf %s',
            'GPRINT:lcdef2:MAX:Maximum\\:%8.2lf %s'])
cmd = [c.strip() for c in cmd if c.strip()]
import rrdtool
rrdtool.graph(*cmd)
graph = read(fname)
