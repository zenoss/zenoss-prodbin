##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os
import rrdtool
import re

try:
    import Globals
    from Products.ZenRRD.plugins.plugin import *
except ImportError:
    from plugin import *

title = 'Area Line Graph'
label = ''
width = 500
height = 100
area = 'ifInOctets'
line = 'ifOutOctets'
areaLabel = 'In'
lineLabel = 'Out'
start='-7d'
end='now'
rpn = ''

env = locals().copy()
args = getArgs(REQUEST, env)
for k, v in env.items():
    locals()[k] = v
fname = "%s/graph-%s.png" % (TMPDIR,name)
afiles = []
lfiles = []
from Products.ZenUtils.Utils import zenPath
perf = zenPath('perf')
devPat = re.compile('.*(%s).*' % env.get('devices',''))
for d, _, fs in os.walk(perf):
    if not devPat.match(d): continue
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
asum = ','.join(('d%d,UN,0,d%d,IF' % (i, i)) for i in range(acount)) + ',+'*(acount-1)
lsum = ','.join(('d%d,UN,0,d%d,IF' % (i, i)) for i in range(acount, count)) + ',+'*(count - acount-1)
for i, s in enumerate([asum, lsum]):
    cdefs.append('CDEF:c%d=%s%s' % (i, s, rpn))
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
stacks.append('AREA:c0#0F0')
stacks.append('LINE:c1#00B')
cmd = [fname] + basicArgs(env) + args + defs + cdefs + [lcdef1, lcdef2] + stacks 
cmd.extend(['GPRINT:lcdef1:LAST:%(areaLabel)s Current\\:%%8.2lf %%s' % env,
            'GPRINT:lcdef1:AVERAGE:Average\\:%8.2lf %s',
            'GPRINT:lcdef1:MAX:Maximum\\:%8.2lf %s\\n'])
cmd.extend(['GPRINT:lcdef2:LAST:%(lineLabel)s Current\\:%%8.2lf %%s' % env,
            'GPRINT:lcdef2:AVERAGE:Average\\:%8.2lf %s',
            'GPRINT:lcdef2:MAX:Maximum\\:%8.2lf %s'])
cmd = [c.strip() for c in cmd if c.strip()]
import rrdtool
graph = None
if defs:
    for c in cmd:
        print "'%s' \\" % c
    rrdtool.graph(*cmd)
    graph = read(fname)
