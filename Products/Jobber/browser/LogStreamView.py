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

import time

from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ZopeTwoPageTemplateFile
from Products.Jobber.logfile import MESSAGE_MARKER, SEEK_END, EOF_MARKER
from Products.ZenUtils.Utils import is_browser_connection_open

class LogStreamView(BrowserView):
    """
    Stream output from a job to the browser.
    """
    def __call__(self):
        self.request.response.setHeader("Content-Type", "text/html")
        self.request.response.write("""
            <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML Basic 1.0//EN"
            "http://www.w3.org/TR/xhtml-basic/xhtml-basic10.dtd">
            <html><body style="overflow-x:hidden;"><pre style="
                font-family:Monaco,monospace;
                font-size:14px;">""")
        self._stream()
        self.request.response.write(""" </pre></body></html> """)
        self.request.response.flush()
        return self.request.response

    def _stream(self):
        log = self.context.getLog()
        f = log.getFile()
        offset = 0
        f.seek(0, SEEK_END)
        remaining = f.tell()
        _wrote = False
        # The while loop keeps the thread open, so check manually to see if
        # the connection has been closed so we don't stream forever
        while is_browser_connection_open(self.request):
            for line in log.generate_lines(f, offset, remaining):
                if line.startswith(EOF_MARKER):
                    return
                self._write_line(line)
                _wrote = True
            if log.finished:
                return
            offset = f.tell()
            f.seek(0, SEEK_END)
            remaining = f.tell() - offset
            del f
            f = log.getFile()
            if not _wrote:
                time.sleep(0.1)
            _wrote = False

    def _write_line(self, line):
        if line.startswith(MESSAGE_MARKER):
            line = """</pre><pre style="
            font-family:Monaco,monospace;
            font-size:14px;color:blue">%s</pre>
           <pre style="
            font-family:Monaco,monospace;
            font-size:14px;">""" % line.lstrip(MESSAGE_MARKER)
        self.request.response.write(line)
        self.request.response.flush()

class LogStreamWrapper(BrowserView):
    """
    Show a log stream in an IFRAME.
    """
    __call__ = ZopeTwoPageTemplateFile('joblogview.pt')

    def stream_URI(self):
        return self.context.absolute_url_path() + '/logstream'

    def description(self):
        job = self.context.getJob()
        type = job.getJobType()
        description = job.getDescription()
        return '%s "%s"' % (type, description)
