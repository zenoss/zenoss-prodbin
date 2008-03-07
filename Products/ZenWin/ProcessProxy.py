###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__ = "Call a python object via an external process"

# Avoid importing Globals:
# from Products.ZenUtils.Utils import zenPath
import os
def zenPath(*parts):
    return os.path.join(os.environ['ZENHOME'], *parts)
import sys
import pickle
import select
import signal
import struct
import time
import fcntl
from subprocess import Popen, PIPE

class ProcessProxyError(Exception): pass
class EofError(ProcessProxyError): pass
class NoProcess(ProcessProxyError): pass
class TimeoutError(ProcessProxyError): pass

class Record(object): pass

class ProcessProxy:

    def __init__(self, filename, classname):
        self.process = None
        self.filename = filename
        self.classname = classname

    def start(self, timer, *args, **kw):
        # spawn process, invoke ctor with args
        self.process = Popen([zenPath('bin/python'),
                              zenPath('Products/ZenWin/ProcessProxy.py')],
                             stdin=PIPE,
                             stdout=PIPE,
                             close_fds=True)
        fcntl.fcntl(self.process.stdout, fcntl.F_SETFL, os.O_NONBLOCK)
        args = pickle.dumps( (args, kw) )
        self.boundedCall(timer, self.filename, self.classname, args)

    def stop(self):
        if self.process:
            os.kill(self.process.pid, signal.SIGKILL)
        self.process = None

    def boundedCall(self, timer, method, *args, **kw):
        try:
            return self._boundedCall(timer, method, *args, **kw)
        except ProcessProxyError, ex:
            self.stop()
            raise
        except Exception, ex:
            raise
        
    def _boundedCall(self, timer, method, *args, **kw):
        if not self.process:
            raise NoProcess
        request = pickle.dumps( (method, args, kw) )
        message = struct.pack("L", len(request)) + request
        stopTime = time.time() + timer
        while message:
            waitTime = stopTime - time.time()
            if waitTime < 0:
                raise TimeoutError
            rd, wr, ex = select.select([], [self.process.stdin], [], waitTime)
            if not wr:
                raise TimeoutError
            self.process.stdin.write(message)
            message = ''
        waitTime = stopTime - time.time()
        rd, wr, ex = select.select([self.process.stdout], [], [], waitTime)
        if not rd:
            raise TimeoutError
        response = self.process.stdout.read(4)
        if not response:
            raise EofError
        responseLen, = struct.unpack("L", response)
        response = ''
        while len(response) < responseLen:
            waitTime = stopTime - time.time()
            if waitTime < 0:
                raise TimeoutError
            rd, wr, ex = select.select([self.process.stdout], [], [], waitTime)
            if not rd:
                raise TimeoutError
            more = self.process.stdout.read(responseLen - len(response))
            if not more:
                raise EofError
            response += more
        success, value = pickle.loads(response)
        if success:
            return value
        raise value

def run():
    import sys
    obj = None
    while 1:
        length = sys.stdin.read(4)
        if not length:
            sys.exit(0)
        if obj is None:
            filename, args, kw = pickle.load(sys.stdin)
            classname = args[0]
            args = args[1]
            fp = open(filename)
            try:
                locals = {}
                exec fp in locals
                args, kw = pickle.loads(args)
                obj = locals[classname](*args, **kw)
            finally:
                fp.close()
            result = (True, None)
        else:
            meth, args, kw = pickle.load(sys.stdin)
            try:
                result = (True, getattr(obj, meth)(*args, **kw))
            except Exception, ex:
                result = (False, ex)
        try:
            result = pickle.dumps(result)
        except Exception, ex:
            result = pickle.dumps( (False, ValueError("Unable to pickle %r" % (result, ))))
        sys.stdout.write(struct.pack('L', len(result)) + result)
        sys.stdout.flush()
                

if __name__=='__main__':
    run()
