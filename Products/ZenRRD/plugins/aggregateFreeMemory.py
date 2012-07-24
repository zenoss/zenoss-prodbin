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
import re
import rrdtool
try:
    import Globals
    from Products.ZenRRD.plugins.plugin import *
except ImportError:
    from plugin import *

title = 'Aggregate Free Memory'
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
cmd = [fname,
       '--imgformat=PNG',
       '--start=%(start)s' % env,
       '--end=%(end)s' % env,
       '--title=%(title)s' % env,
       '--base=1000',
       '--height=%(height)s' % env,
       '--width=%(width)s' % env,
       '--vertical-label=%(label)s' % env] + args
ifiles = []
ofiles = []
from Products.ZenUtils.Utils import zenPath
perf = zenPath('perf')
rpn = env['rpn']
devicePat = re.compile('.*(' + env.get('devices', '') + ').*')
for d, _, fs in os.walk(perf):
    if not devicePat.match(d): continue
    for f in fs:
        if f.find('memAvailReal') >= 0:
            ifiles.append(os.path.join(d, f))
        if f.find('memCached') >= 0:
            ifiles.append(os.path.join(d, f))
        if f.find('memBuffer') >= 0:
            ifiles.append(os.path.join(d, f))
        if f.find('memoryAvailableKBytes') >= 0:
            ofiles.append(os.path.join(d, f))
files = ifiles + ofiles
count = len(files)

defs = []
for i, f in enumerate(files):
    defs.append('DEF:d%d=%s:ds0:AVERAGE' % (i, f))
cdefs = []
for i, f in enumerate(files):
    if f.find("/mem_") >= 0:
        cdefs.append('CDEF:c%d=d%d,1024,/%s' % (i, i, rpn))
    else:
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
    stacks.append('AREA:c%d%s::STACK' % (i, color))
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
