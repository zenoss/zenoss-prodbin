###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import os
import time
from cStringIO import StringIO
from posixfile import SEEK_END

EOF_MARKER = '<<<<<EOF>>>>>'

class LogFile(object):

    def __init__(self, status, logfilename):
        self.status = status
        self.finished = status.isFinished()
        self.filename = logfilename
        fn = self.getFilename()
        self.openfile = open(fn, "a+")

    def getFilename(self):
        return self.filename

    def hasContents(self):
        return os.path.exists(self.getFilename())

    def getStatus(self):
        return self.status

    def getFile(self):
        if self.openfile:
            # Don't close this, because we're using it to write
            return self.openfile
        # Please to enjoy a read-only handle
        return open(self.getFilename(), "r")

    def getText(self):
        f = self.getFile()
        f.seek(0)
        return f.read()

    def readlines(self):
        io = StringIO(self.getText())
        return io.readlines()

    def getLines(self):
        f = self.getFile()
        offset = 0
        f.seek(0, SEEK_END)
        remaining = f.tell()
        return self._generate_lines(f, offset, remaining)

    def _generate_lines(self, f, offset, remaining):
        f.seek(offset)
        for line in f.readlines(remaining):
            yield line
        del f

    def write(self, text):
        f = self.openfile
        f.seek(0, SEEK_END)
        offset = 0
        f.write(text)
        f.flush()

    def stream(self):
        f = self.getFile()
        offset = 0
        f.seek(0, SEEK_END)
        remaining = f.tell()
        while True:
            for line in self._generate_lines(f, offset, remaining):
                if line.startswith(EOF_MARKER):
                    raise StopIteration
                yield line
            if self.finished:
                break
            offset = f.tell()
            f.seek(0, SEEK_END)
            remaining = f.tell() - offset
            del f
            time.sleep(0.1)
            f = self.getFile()

    def finish(self):
        if self.openfile:
            self.write('\n%s' % EOF_MARKER)
            os.fsync(self.openfile.fileno())
            del self.openfile

