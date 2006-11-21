import rrdtool
import re
import Globals
try:
    from Products.ZenRRD.plugins.plugin import *
except ImportError:
    from plugin import *

locals().setdefault('REQUEST', None)
locals().setdefault('name', 'test')
if locals().has_key('self'):
    dmd = self.dmd
if not locals().has_key('dmd'):
    from Products.ZenUtils.ZCmdBase import ZCmdBase
    locals()['dmd'] = ZCmdBase().dmd

title = 'Aggregate Network Throughput'
label = 'Mbs'
devices='.*'
env = locals().copy()
args = getArgs(REQUEST, env)

fname = "%s/graph-%s.png" % (TMPDIR,name)
files = []
defs = []
cdefs = []
xdefs = []
stacks=[]
lcdef = ['CDEF:lcdef=']
lcolors = len(colors)
devicePat = re.compile('.*' + env['devices'] + '.*')
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
                rrdfile = perf + interface.getRRDFileName(dp.name())
                if not os.path.exists(rrdfile): continue
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
