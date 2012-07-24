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

title = 'Aggregate Network Throughput'
label = 'Mbs'
devices='.*'
env = locals().copy()
args = getArgs(REQUEST, env)
for k, v in env.items():
    locals()[k] = v
fname = "%s/graph-%s.png" % (TMPDIR,name)
files = []
defs = []
cdefs = []
xdefs = []
stacks=[]
lcdef = ['CDEF:lcdef=']
lcolors = len(colors)
devicePat = re.compile('.*(' + env['devices'] + ').*')
files = []
n = 0
for i, d in enumerate(dmd.Devices.getSubDevices()):
    if not devicePat.match(d.id): continue
    for j, interface in enumerate(d.os.interfaces()):
        template = interface.getRRDTemplate()
        try:
            graph = template.graphs['Throughput']
        except KeyError:
            continue
        else:
            for ds in graph.dsnames:
                dp = template.getRRDDataPoint(ds)
                if not dp: continue
                rrdfile = perf + interface.getRRDFileName(dp.id)
                files = glob.glob(rrdfile)
                if len(files) != 1: continue
                rrdfile = files[0]
                dir = 1
                if ds.find("ifInOctets") >= 0:
                    dir = -1
                    color = colors[i]
                else:
                    color = colors[i]
                defs.append('DEF:d%d=%s:ds0:AVERAGE' % (n, rrdfile))
                cdefs.append('CDEF:c%d=d%d,%d,*' % (n, n, dir))
                xdefs.append('CDEF:x%d=d%d' % (n, n))
                stacks.append('AREA:c%d#%s::STACK' % (n, color))
                lcdef.append('TIME,%d,GT,x%d,x%d,UN,0,x%d,IF,IF,' % (now, n, n, n))
                n += 1
lcdef.append('+,'*(len(cdefs) - 1))
lcdef = ''.join(lcdef)
args.insert(0, '--units-exponent=6')
cmd = [fname]  + basicArgs(env) + args + defs + xdefs + cdefs + stacks + [lcdef]
cmd.extend(['GPRINT:lcdef:LAST:Current\\:%8.2lf %s',
            'GPRINT:lcdef:AVERAGE:Average\\:%8.2lf %s',
            'GPRINT:lcdef:MAX:Maximum\\:%8.2lf %s'])
cmd = [c.strip() for c in cmd if c.strip()]
import rrdtool
rrdtool.graph(*cmd)
graph = open(fname, 'rb').read()
