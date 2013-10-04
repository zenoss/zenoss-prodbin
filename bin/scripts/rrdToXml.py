#!/usr/bin/env python
import os
import sys
from subprocess import Popen

def rrdToXml(filename):
    print "Exporting %s to XML." % filename
    xmlfile = open(filename.replace('.rrd', '.xml'), 'w')
    Popen(["rrdtool", "dump", filename], stdout=xmlfile)
    xmlfile.close()

if __name__ == '__main__':
    if 'ZENHOME' not in os.environ:
        print >> sys.stderr, "ZENHOME not set. You should be the zenoss user."
        sys.exit(1)

    perf_dir = os.path.join(os.environ['ZENHOME'], 'perf')

    for path, dirs, files in os.walk(perf_dir):
        for file in [ os.path.join(path, f) for f in files ]:
            if not file.endswith('.rrd'): continue
            rrdToXml(file)
