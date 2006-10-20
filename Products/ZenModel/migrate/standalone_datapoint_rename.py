#!/usr/bin/python
import os
for d, dirs, filenames in os.walk(os.path.join(os.environ['ZENHOME'], 'perf')):
    for f in filenames:
        fullpath = os.path.join(d, f)
        if f.find('_') >= 0: continue
        if not f.endswith('.rrd'): continue
	base = os.path.basename(f[:-4])
	os.rename(fullpath, os.path.join(d, '%s_%s.rrd' % (base, base)))
