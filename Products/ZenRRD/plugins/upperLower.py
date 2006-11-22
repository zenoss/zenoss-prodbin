import os
import time
import glob
import rrdtool
import random
import re
try:
    import Globals
    from Products.ZenRRD.plugins.plugin import *
except ImportError:
    from plugin import *

# set variables for command-line testing
locals().setdefault('REQUEST', None)
locals().setdefault('name', 'test')

title = 'Upper Lower Graph'
label = ''
width = 500
height = 100
# lower = 'ifInOctets'
lower = 'ifOutOctets'
upper = 'ifOutOctets'
lowerLabel = 'In'
upperLabel = 'Out'
start='-7d'
end='now'
rpn = ''
devices='.*'

env = locals().copy()
if REQUEST:
    REQUEST.response.setHeader('Content-type', 'image/png')
    env.update(dict(zip(REQUEST.keys(), REQUEST.values())))
fname = "%s/graph-%s.png" % (TMPDIR,name)
args = getArgs(REQUEST, env)
args = args or ['--units-exponent=6']
for k, v in env.items():
    locals()[k] = v
lfiles = []
ufiles = []
perf = os.path.join(os.environ['ZENHOME'], 'perf')
rpn = env['rpn']
devPat = re.compile('.*%s.*' % devices)
for d, _, fs in os.walk(perf):
    if not devPat.match(d): continue
    for f in fs:
        if f.find(lower) >= 0:
            lfiles.append(os.path.join(d, f))
        if f.find(upper) >= 0:
            ufiles.append(os.path.join(d, f))
files = lfiles + ufiles
lcount = len(lfiles)
count = len(files)

defs = []
for i, f in enumerate(files):
    defs.append('DEF:d%d=%s:ds0:AVERAGE' % (i, f))
cdefs = []
for i in range(lcount):
    cdefs.append('CDEF:c%d=d%d,-1,*%s' % (i, i, rpn))
for i in range(lcount, count):
    cdefs.append('CDEF:c%d=d%d%s' % (i, i, rpn))
lcdef = ['CDEF:lcdef1=']
for i in range(lcount):
    lcdef.append('TIME,%d,GT,d%d,d%d,UN,0,d%d,IF,IF,' % (now, i, i, i))
lcdef.append('+,'*(lcount-1))
if rpn:
    lcdef.append(rpn[1:])
lcdef1 = ''.join(lcdef)
lcdef = ['CDEF:lcdef2=']
for i in range(lcount, count):
    lcdef.append('TIME,%d,GT,d%d,d%d,UN,0,d%d,IF,IF,' % (now, i, i, i))
lcdef.append('+,'*(count-lcount-1))
if rpn:
    lcdef.append(rpn[1:])
lcdef2 = ''.join(lcdef)
stacks=[]
inputFilesCount = len(lfiles)
lcolor = len(colors)
for i in range(count):
    stacks.append('AREA:c%d#%s::STACK' % (i, colors[i % lcolor]))
cmd = [fname] + basicArgs(env) + defs + cdefs + [lcdef1, lcdef2] + stacks
cmd.extend(['GPRINT:lcdef2:LAST:%s Current\\:%%8.2lf %%s' % upperLabel,
            'GPRINT:lcdef2:AVERAGE:Average\\:%8.2lf %s',
            'GPRINT:lcdef2:MAX:Maximum\\:%8.2lf %s\\n'])
cmd.extend(['GPRINT:lcdef1:LAST:%s Current\\:%%8.2lf %%s' % lowerLabel,
            'GPRINT:lcdef1:AVERAGE:Average\\:%8.2lf %s',
            'GPRINT:lcdef1:MAX:Maximum\\:%8.2lf %s\\n'])
cmd = [c.strip() for c in cmd if c.strip()]
import rrdtool
print cmd
rrdtool.graph(*cmd)
graph = read(fname)
