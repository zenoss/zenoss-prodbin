import rrdtool
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
perf = os.path.join(os.environ['ZENHOME'], 'perf')

title = 'Aggregate Disk Use'
label = 'Gigabytes'
width = 500
height = 100
start='-7d'
end='now'
env = locals().copy()
args = []
locals().setdefault('name', 'test')

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
       '--vertical-label=%(label)s' % env] + args

total = 0l
files = []
defs = []
cdefs = []
lcdef = ['CDEF:lcdef=']
stacks=[]
colors = 'FFFFCC FFFF33 FFCCCC FFCC33 FF99CC FF9933 FF66CC FF6633 FF33CC FF3333 FF00CC FF0033'.split()
lcolors = len(colors)
for i, f in enumerate(dmd.Devices.getSubComponents(meta_type='FileSystem')):
    available = f.totalBlocks * f.blockSize
    rrdFile = perf + f.getRRDFileName('usedBlocks_usedBlocks')
    if not os.path.exists(rrdFile):
        rrdFile = perf + f.getRRDFileName('disk_usedBlocks')
    files.append(rrdFile)
    defs.append('DEF:d%d=%s:ds0:AVERAGE' % (i, rrdFile))
    cdefs.append('CDEF:c%d=d%d,%d,*' % (i, i, f.blockSize))
    lcdef.append('TIME,%d,GT,c%d,c%d,UN,0,c%d,IF,IF,' % (time.time(), i, i, i))
    stacks.append('AREA:c%d#%s::STACK' % (i, colors[i % lcolors]))
    total += available
lcdef.append('+,'*(len(files) - 1))

cmd += defs + cdefs + [''.join(lcdef)] + stacks 
if not env.get('nolimit'):
    cmd.append('LINE:%s#000:Total Disk Space\\: %8.2lfG'% (total, (total / (1024**3))))
cmd.extend(['GPRINT:lcdef:LAST:Current\\:%8.2lf %s',
            'GPRINT:lcdef:AVERAGE:Average\\:%8.2lf %s',
            'GPRINT:lcdef:MAX:Maximum\\:%8.2lf %s'])
cmd = [c.strip() for c in cmd if c.strip()]
import rrdtool
rrdtool.graph(*cmd)
graph = open(fname, 'rb').read()
