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
try:
    import Globals
    from Products.ZenRRD.plugins.plugin import *
except ImportError:
    from plugin import *

title = 'Aggregate Network Traffic'
label = 'Mbs'
width = 500
height = 100
start='-1d'
end='now'
rpn = ',8,*'

env = locals().copy()
args = getArgs(REQUEST, env)
for k, v in env.items():
    locals()[k] = v
fname = "%s/graph-%s.png" % (TMPDIR,name)
cmd = [fname,] + basicArgs(env) + ['--base=1000',
                                   '--vertical-label=%(label)s' % env]
ifiles = []
ofiles = []
from Products.ZenUtils.Utils import zenPath
perf = zenPath('perf')
rpn = env['rpn']
for d, _, fs in os.walk(perf):
    for f in fs:
        if f.find('ifInOctets') >= 0:
            ifiles.append(os.path.join(d, f))
        if f.find('ifOutOctets') >= 0:
            ofiles.append(os.path.join(d, f))
files = ifiles + ofiles
count = len(files)

defs = []
for i, f in enumerate(files):
    defs.append('DEF:d%d=%s:ds0:AVERAGE' % (i, f))
cdefs = []
for i in range(count):
    cdefs.append('CDEF:c%d=d%d%s' % (i, i, rpn))
lcdef = ['CDEF:lcdef=']
now = time.time()
for i in range(count):
    lcdef.append('TIME,%d,GT,d%d,d%d,UN,0,d%d,IF,IF,' % (now, i, i, i))
lcdef.append('+,'*(len(files) - 1))
if rpn:
    lcdef.append(rpn[1:])
stacks=[]
inputFilesCount = len(ifiles)
for i in range(count):
    color =  (0xf00f037 << (i % 24))
    if i < inputFilesCount:
        color |= 0x707070
    color = '#%06x' % (color & 0xffffff)
    if i == 0:
        stacks.append('AREA:c%d%s' % (i, color))
    else:
        stacks.append('STACK:c%d%s' % (i, color))
cmd.extend(defs)
cmd.extend(cdefs)
cmd.append(''.join(lcdef))
cmd.extend(stacks)
cmd.extend(['GPRINT:lcdef:LAST:Current\\:%8.2lf %s',
            'GPRINT:lcdef:AVERAGE:Average\\:%8.2lf %s',
            'GPRINT:lcdef:MAX:Maximum\\:%8.2lf %s'])
cmd = [c.strip() for c in cmd if c.strip()]
import rrdtool
rrdtool.graph(*cmd)
graph = read(fname)
