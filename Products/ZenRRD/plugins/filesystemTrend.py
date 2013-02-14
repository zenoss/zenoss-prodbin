##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import rrdtool
try:
    import Globals
    from Products.ZenRRD.plugins.plugin import getArgs, REQUEST, TMPDIR, name, basicArgs, read
except ImportError:
    from plugin import getArgs, REQUEST, TMPDIR, name, basicArgs, read

from time import time

if 'self' in locals():
    dmd = self.dmd
if 'dmd' not in locals():
    from Products.ZenUtils.ZCmdBase import ZCmdBase
    locals()['dmd'] = ZCmdBase().dmd

title = 'Filesystem Trend'
label = 'Percent Utilization'
width = 500
height = 120
start = '-2w'
end = 'now+1w'

env = locals().copy()
args = getArgs(REQUEST, env)
for k, v in env.items():
    locals()[k] = v

fname = "%s/graph-%s.png" % (TMPDIR,name)

# Pull device for the given name
#
device = env['device']
dev = dmd.Devices.findDevice(device)

# Take the filesytem name and grab its corresponding filesystem
# object.
#
fsname = env['filesystem']
fs = dev.os.filesystems._getOb(fsname)
totalBlocks = fs.totalBlocks

env['title'] += ' - %s' % env['device']
if fsname:
    env['title'] += ':/'
    if fsname != '-':
        env['title'] += fsname.replace('_','/')

# We look for only the usedBlocks_usedBlock datapoint
#
rrdfile = ''
for fname in fs.getRRDNames():
    if fname == 'usedBlocks_usedBlocks':
        rrdfile = fs.getRRDFileName(fname)
        break

if rrdfile:
    rrdfile = '/opt/zenoss/perf/' + rrdfile

cmd = [fname] + basicArgs(env) + args 

cmd.extend(['-E', '-l 0', '-u 100', '-r',
            '-W SunGard Availability Services'])

# This smooths the trend lines, but makes the graph a little blurry.
# Comment it out for crisper graph and stair-step trend lines.
cmd.extend(['-N'])

# Take blocks_used DEFS (datasets for differing time periods).
# and calculate filesytem usage as a percentage into the fsu_x cdefs.
#
cmd.extend([
    'DEF:used_blocks_a=%s:ds0:AVERAGE:' % rrdfile,
    'DEF:used_blocks_b=%s:ds0:AVERAGE:start=now-3d' % rrdfile,
    'DEF:used_blocks_c=%s:ds0:AVERAGE:start=now-1w' % rrdfile,
    'DEF:used_blocks_d=%s:ds0:AVERAGE:start=now-1m' % rrdfile,
    'CDEF:fsu_a=used_blocks_a,%s,/,100,*' % totalBlocks,
    'CDEF:fsu_b=used_blocks_b,%s,/,100,*' % totalBlocks,
    'CDEF:fsu_c=used_blocks_c,%s,/,100,*' % totalBlocks,
    'CDEF:fsu_d=used_blocks_d,%s,/,100,*' % totalBlocks])

# VDEFS for slope based on Least Squares Line (LSL) against filesystem
# usage data.
#
cmd.extend([
    'VDEF:slope_a=fsu_a,LSLSLOPE',
    'VDEF:yint_a=fsu_a,LSLINT',
    'VDEF:correl_a=fsu_a,LSLCORREL',
    'VDEF:slope_b=fsu_b,LSLSLOPE',
    'VDEF:yint_b=fsu_b,LSLINT',
    'VDEF:correl_b=fsu_b,LSLCORREL',
    'VDEF:slope_c=fsu_c,LSLSLOPE',
    'VDEF:yint_c=fsu_c,LSLINT',
    'VDEF:correl_c=fsu_c,LSLCORREL',
    'VDEF:slope_d=fsu_d,LSLSLOPE',
    'VDEF:yint_d=fsu_d,LSLINT',
    'VDEF:correl_d=fsu_d,LSLCORREL'])

# Generate the slope line projection data set.
#
cmd.extend([
    'CDEF:projuse_a=fsu_a,POP,yint_a,slope_a,COUNT,*,+',
    'CDEF:fyline_a=projuse_a,0,100,LIMIT',
    'CDEF:projuse_b=fsu_b,POP,yint_b,slope_b,COUNT,*,+',
    'CDEF:fyline_b=projuse_b,0,100,LIMIT',
    'CDEF:projuse_c=fsu_c,POP,yint_c,slope_c,COUNT,*,+',
    'CDEF:fyline_c=projuse_c,0,100,LIMIT',
    'CDEF:projuse_d=fsu_d,POP,yint_d,slope_d,COUNT,*,+',
    'CDEF:fyline_d=projuse_d,0,100,LIMIT'])

# Get the last value off of the projected data set.
#
cmd.extend([
    'VDEF:firstv=fsu_a,FIRST',
    'VDEF:lastv=projuse_a,LAST'])

# Mark the 100% crossover time (anything over 99.99%).
# (walk a trend data set, if slope is positive and the value is
#  > 99.99, then set value to infinity, otherwise set to unknown).
#
cmd.extend([
    'CDEF:crosslimit_a=projuse_a,99.99,INF,LIMIT,UN,UNKN,slope_a,0,LT,UNKN,TIME,IF,IF',
    'CDEF:crosslimit_b=projuse_b,99.99,INF,LIMIT,UN,UNKN,slope_b,0,LT,UNKN,TIME,IF,IF',
    'CDEF:crosslimit_c=projuse_c,99.99,INF,LIMIT,UN,UNKN,slope_c,0,LT,UNKN,TIME,IF,IF',
    'CDEF:crosslimit_d=projuse_d,99.99,INF,LIMIT,UN,UNKN,slope_d,0,LT,UNKN,TIME,IF,IF'])

# Pull the first known value from the crosslimit data sets defined
# above. This will be the first value that hit the 100% mark.
# Use the :strftime argument to gprint to print the timestamp of
# this value later.
#
cmd.extend([
    'VDEF:co_limit_a=crosslimit_a,FIRST',
    'VDEF:co_limit_b=crosslimit_b,FIRST',
    'VDEF:co_limit_c=crosslimit_c,FIRST',
    'VDEF:co_limit_d=crosslimit_d,FIRST'])

cmd.extend([
    'GPRINT:firstv:Period between %x\g:strftime',
    'GPRINT:lastv: and %x\c:strftime',
    'COMMENT:\\s'])

# Create a 1/16th slice to use for our gradient.
#
cmd.extend(['CDEF:fsu_by_16=fsu_a,16,/'])

# Draw the base area using our base color (slight transparent yellow).
#
cmd.extend(['AREA:fsu_a#FFCC0066'])

# Then draw the gradient on top of the base (using green
# but changing the transparency of each slice.

cmd.extend([
    'AREA:fsu_by_16#33BC3300',
    'AREA:fsu_by_16#33BC3311::STACK',
    'AREA:fsu_by_16#33BC3322::STACK',
    'AREA:fsu_by_16#33BC3333::STACK',
    'AREA:fsu_by_16#33BC3344::STACK',
    'AREA:fsu_by_16#33BC3355::STACK',
    'AREA:fsu_by_16#33BC3366::STACK',
    'AREA:fsu_by_16#33BC3377::STACK',
    'AREA:fsu_by_16#33BC3388::STACK',
    'AREA:fsu_by_16#33BC3399::STACK',
    'AREA:fsu_by_16#33BC33AA::STACK',
    'AREA:fsu_by_16#33BC33BB::STACK',
    'AREA:fsu_by_16#33BC33CC::STACK',
    'AREA:fsu_by_16#33BC33DD::STACK',
    'AREA:fsu_by_16#33BC33EE::STACK',
    'AREA:fsu_by_16#33BC33FF::STACK'])

# Top it all off with a darker line for contrast.
#
cmd.extend(['LINE:fsu_a#116611'])

# Now our ledgends and other info
#
cmd.extend([
    'COMMENT:Projection\\t\\t',
    'COMMENT:Corr-Coefficient\\l',
    'COMMENT:--------------------\\t',
    'COMMENT:----------------\\l'])

cmd.extend([
    'LINE2:fyline_a#FC900098:From graph start\\t',
    'GPRINT:correl_a:%10.2lf\\t',
    'COMMENT: \\l'])

cmd.extend([
    'LINE2:fyline_b#CC000098:From 3 days ago \\t',
    'GPRINT:correl_b:%10.2lf\\t',
    'COMMENT: \\l'])

cmd.extend([
    'LINE2:fyline_c#00CCCC98:From 1 week ago \\t',
    'GPRINT:correl_c:%10.2lf\\t',
    'COMMENT: \\l'])

cmd.extend([
    'LINE2:fyline_d#0000CC98:From 1 month ago\\t',
    'GPRINT:correl_d:%10.2lf\\t',
    'COMMENT: \\l'])

# A vrule marking the current date/time
#
cmd.extend(['VRULE:%s#66666666' % int(time())])

cmd = [c.strip() for c in cmd if c.strip()]

graph = None
if rrdfile:
    rrdtool.graph(*cmd)
    graph = read(fname)

