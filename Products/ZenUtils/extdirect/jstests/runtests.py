#! /usr/bin/env python

# You must set up the PYTHONPATH this way...
#
#   PYTHONPATH="$ZENHOME:$PYTHONPATH" ./runtests.py
#

import os
import subprocess
import time
import re

def main(modules):
    
    # the http server process
    httpd = subprocess.Popen(['python', 'server.py'])
    time.sleep(1)
    
    # the rhino process
    rhino = subprocess.Popen(['java', '-jar', 'env-js.jar'],
                             stdin=subprocess.PIPE,
                             cwd='lib')
                             
    if not modules:
        # no modules specified on command line. run all modules.
        modules = [m for m in os.listdir('modules') if re.match(r'[^._]', m)]
    moduleLoads = ["load('../modules/%s/runtest.js')\n" % m for m in modules]
    
    rhino.stdin.write("load('init.js')\n")
    rhino.stdin.writelines(moduleLoads)
    rhino.stdin.write("load('main.js')\n")
    
    # wait for rhino to terminate
    while True:
        if rhino.poll() is not None:
            break
        time.sleep(1)
    
    os.kill(httpd.pid, 9)
    return rhino.returncode
    
if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))
    
