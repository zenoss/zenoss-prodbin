##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os
import time
from Products.ZenUtils.Utils import rrd_daemon_args

TMPDIR='/tmp/renderserver'
if not os.path.exists(TMPDIR):
    os.makedirs(TMPDIR, 0750)

colors = [s.strip()[1:] for s in '''
#00FF99
#00FF00
#00CC99
#00CC00
#009999
#009900
#006699
#006600
#003399
#003300
#000099
#000000
'''.split()]


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
        if os.stat(fname).st_mtime > time.time() - cachedTime:
            return read(fname)
    except OSError:
        return None

from Products.ZenUtils.Utils import zenPath
perf =  zenPath('perf')

title = 'Plugin Title'
label = ''
width = 500
height = 100
start='-7d'
end='now'
name='test'

def basicArgs(env):
    args = ['--imgformat=PNG',
            '--start=%(start)s' % env,
            '--end=%(end)s' % env,
            '--title=%(title)s' % env,
            '--height=%(height)s' % env,
            '--width=%(width)s' % env,
            '--vertical-label=%(label)s' % env]
    daemon_args = rrd_daemon_args()
    if daemon_args:
        args.append('='.join(daemon_args))
    return args

def getArgs(REQUEST, env):
    env.setdefault('arg', [])
    args = []
    if REQUEST:
        REQUEST.response.setHeader('Content-type', 'image/png')
        kv = zip(REQUEST.keys(), REQUEST.values())
        env.update(dict(kv))
    miny = env.get('miny', '')
    maxy = env.get('maxy', '')
    if miny:
        del env['miny']
        args.append('--lower-limit=%s' % miny)
    if maxy:
        del env['maxy']
        args.append('--upper-limit=%s' % maxy)
    if miny or maxy:
        args.append('-r')
    if isinstance(env['arg'], basestring):
        args = [env['arg']] + args
    else:
        args += env['arg']
    env['arg'] = args
    return args

    
now = time.time()
