import os
import time

TMPDIR='/tmp/renderserver'
if not os.path.exists(TMPDIR):
    os.makedirs(TMPDIR)

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

perf = os.path.join(os.environ['ZENHOME'], 'perf')

title = 'Plugin Title'
label = ''
width = 500
height = 100
start='-7d'
end='now'
name='test'

def basicArgs(env):
    return ['--imgformat=PNG',
            '--start=%(start)s' % env,
            '--end=%(end)s' % env,
            '--title=%(title)s' % env,
            '--height=%(height)s' % env,
            '--width=%(width)s' % env,
            '--vertical-label=%(label)s' % env]

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
    if type(env['arg']) == type(''):
        args = [env['arg']] + args
    else:
        args += env['arg']
    env['arg'] = args
    return args

    
now = time.time()
