##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
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
    from Products.ZenRRD.plugins.plugin import getArgs, REQUEST, TMPDIR, name, basicArgs, read, now
except ImportError:
    from plugin import getArgs, REQUEST, TMPDIR, name, basicArgs, read, now

if 'self' in locals():
    dmd = self.dmd
if 'dmd' not in locals():
    from Products.ZenUtils.ZCmdBase import ZCmdBase
    locals()['dmd'] = ZCmdBase().dmd

title = 'Device Aggregate Network Traffic'
label = 'bps in <-0-> bps Out'
width = 500
height = 100
lower = 'ifInOctets'
upper = 'ifOutOctets'
hcLower = 'ifHCInOctets'
hcUpper = 'ifHCOutOctets'
lowerLabel = 'Incoming'
upperLabel = 'Outgoing'
start = '-7d'
end = 'now'
rpn = ''

env = locals().copy()
args = getArgs(REQUEST, env)
for k, v in env.items():
    locals()[k] = v
fname = "%s/graph-%s.png" % (TMPDIR,name)
lfiles = []
ufiles = []

colors = [s.strip()[1:] for s in '''
#3333ff
#33ff33
#ff3333
#66ffff
#ffff66
#ff66ff
#9999ff
#99ff99
#ff9999
#33ff99
#ff9933
#9933ff
#66ffcc
#ffcc66
#cc66ff
'''.split()]


# Pull device for the given name
#
device = env['device']
dev = dmd.Devices.findDevice(device)

env['title'] += ' - %s' % env['device']

# Get zProp for net if regex
#
devPat = None
if env.has_key('netIfRe'):
    netIfRe = env['netIfRe']
else:
    netIfRe = dev.getZ('zNetInterfacesGraphRegex')

if netIfRe:
    devPat = re.compile(netIfRe)

# Construct path to device interfaces
#
perf = os.path.join(dev.os.fullRRDPath(), 'interfaces')

for d, _, fs in os.walk(perf):
    if devPat and not devPat.match(d): continue
    for f in fs:
        if f.find(hcLower) >= 0 or f.find(lower) >= 0:
            lfiles.append(os.path.join(d, f))
        if f.find(hcUpper) >= 0 or f.find(upper) >= 0:
            ufiles.append(os.path.join(d, f))

lcount = len(lfiles)
ucount = len(ufiles)

files = lfiles + ufiles
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
stacks = []
inputFilesCount = len(lfiles)
lcolor = len(colors)

for i in range(lcount):
    stacks.append('AREA:c%d#%s::STACK' % (i, colors[i % lcolor]))

x = 0
if lcount != count:
    stacks.append('AREA:c%d#%s' % (lcount, colors[x % lcolor]))
    x+=1

for i in range(lcount + 1, count):
    stacks.append('AREA:c%d#%s::STACK' % (i, colors[x % lcolor]))
    x+=1

cmd = [fname] + basicArgs(env) + args + defs + cdefs + [lcdef1, lcdef2] + stacks

cmd.extend(['COMMENT:Interface Counts\: incoming=%s outgoing=%s\\c' % (lcount, ucount)])
if netIfRe: cmd.extend(['COMMENT:Filter="%s"\\c' % netIfRe])
cmd.extend(['COMMENT: \\l'])

cmd.extend(['GPRINT:lcdef2:LAST:%(upperLabel)s - Current\\: %%6.2lf %%s' % env,
            'GPRINT:lcdef2:AVERAGE:Average\\: %6.2lf %s',
            'GPRINT:lcdef2:MAX:Maximum\\: %6.2lf %s\\n'])
cmd.extend(['GPRINT:lcdef1:LAST:%(lowerLabel)s - Current\\: %%6.2lf %%s' % env,
            'GPRINT:lcdef1:AVERAGE:Average\\: %6.2lf %s',
            'GPRINT:lcdef1:MAX:Maximum\\: %6.2lf %s\\n'])
cmd = [c.strip() for c in cmd if c.strip()]

graph = None
if defs:
    rrdtool.graph(*cmd)
    graph = read(fname)

