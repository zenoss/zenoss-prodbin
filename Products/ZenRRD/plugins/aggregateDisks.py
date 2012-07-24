##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import rrdtool
import re
import glob
import Globals
from os import path

try:
    from Products.ZenRRD.plugins.plugin import *
except ImportError:
    from plugin import *

locals().setdefault('REQUEST', None)
locals().setdefault('name', 'test')
if 'self' in locals():
    dmd = self.dmd
if not 'dmd' in locals():
    from Products.ZenUtils.ZCmdBase import ZCmdBase
    dmd = ZCmdBase().dmd

title = 'Aggregate Disk Use'
label = 'Gigabytes'
env = locals().copy()
args = getArgs(REQUEST, env)
for k, v in env.items():
    locals()[k] = v
fname = "%s/graph-%s.png" % (TMPDIR,name)

total = 0l
files = []
defs = []
cdefs = []
lcdef = ['CDEF:lcdef=']
stacks=[]
lcolors = len(colors)
devicePat = re.compile('.*' + env.get('devices', '') + '.*')
for i, f in enumerate(dmd.Devices.getSubComponents(meta_type='FileSystem')):
    available = f.totalBlocks * f.blockSize
    rrdFile = os.path.join( perf, f.getRRDFileName('usedBlocks') )
    globbed = glob.glob(rrdFile)
    if len(globbed) == 0: continue
    rrdFile = globbed[0]
    if not devicePat.match(rrdFile): continue
    files.append(rrdFile)
    defs.append('DEF:d%d=%s:ds0:AVERAGE' % (i, rrdFile))
    cdefs.append('CDEF:c%d=d%d,%d,*' % (i, i, f.blockSize))
    lcdef.append('TIME,%d,GT,c%d,c%d,UN,0,c%d,IF,IF,' % (time.time(), i, i, i))
    stacks.append('AREA:c%d#%s::STACK' % (i, colors[i % lcolors]))
    total += available
lcdef.append('+,'*(len(files) - 1))
lcdef = ''.join(lcdef)

cmd = [fname]  + basicArgs(env) + args + defs + cdefs + [lcdef] + stacks 
if not env.get('nolimit'):
    cmd.append('LINE:%s#000:Total Disk Space\\: %8.2lfG'% (total, (total / (1024**3))))
cmd.extend(['GPRINT:lcdef:LAST:Current\\:%8.2lf %s',
            'GPRINT:lcdef:AVERAGE:Average\\:%8.2lf %s',
            'GPRINT:lcdef:MAX:Maximum\\:%8.2lf %s'])
cmd = [c.strip() for c in cmd if c.strip()]
import rrdtool
graph = None
if defs:
    rrdtool.graph(*cmd)
    graph = open(fname, 'rb').read()
