import os
import time

TMPDIR='/tmp/renderserver'
if not os.path.exists(TMPDIR):
    os.makedirs(TMPDIR)
from Products.ZenRRD.plugins.plugin import *

def read(fname):
    "read a file, ensuring that the file is always closed"
    fp = open(fname)
    try:
        return fp.read()
    finally:
        fp.close()

def cached(fname, cachedTime=600):
    "return the contents of a file if it is young enough"
    try:
        if os.stat(fname).st_mtime > time.time() - 600:
            return read(fname)
    except OSError:
        return None

