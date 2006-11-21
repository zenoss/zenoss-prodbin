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
'FF0033 FF00CC FF3333 FF33CC FF6633 FF66CC FF9933 FF99CC FFCC33 FFCCCC FFFF33 FFFFCC'.split()


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
    args = []
    if REQUEST:
        REQUEST.response.setHeader('Content-type', 'image/png')
        kv = zip(REQUEST.keys(), REQUEST.values())
        env.update(dict(kv))
        for k, v in kv:
           if k == 'arg':
              args.append(v)
    return args

    
now = time.time()
