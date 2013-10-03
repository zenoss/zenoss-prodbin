#!/usr/bin/env python
import os
import sys
from subprocess import Popen

def xmlToRRD(filename):
    print "Importing %s from XML." % filename
    rrdfile = filename.replace('.xml', '.rrd')
    try:
        os.unlink(rrdfile)
    except:
        pass
    Popen(["rrdtool", "restore", filename, rrdfile])

if __name__ == '__main__':
    if 'ZENHOME' not in os.environ:
        print >> sys.stderr, "ZENHOME not set. You should be the zenoss user."
        sys.exit(1)

    perf_dir = os.path.join(os.environ['ZENHOME'], 'perf')

    for path, dirs, files in os.walk(perf_dir):
        for file in [ os.path.join(path, f) for f in files ]:
            if not file.endswith('.xml'): continue
            xmlToRRD(file)
