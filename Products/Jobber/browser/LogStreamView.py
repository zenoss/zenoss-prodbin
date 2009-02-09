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

from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ZopeTwoPageTemplateFile
from Products.Jobber.logfile import MESSAGE_MARKER

class LogStreamView(BrowserView):
    """
    Stream output from a job to the browser.
    """
    def __call__(self):
        log = self.context.getLog()
        # Stream me
        self.request.response.setHeader("Content-Type", "text/html")
        self.request.response.write("""
            <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML Basic 1.0//EN"
            "http://www.w3.org/TR/xhtml-basic/xhtml-basic10.dtd">
            <html><body style="overflow-x:hidden;"><pre style="
                font-family:Monaco,monospace;
                font-size:14px;">""")
        for line in log.stream():
            if line.startswith(MESSAGE_MARKER):
                line = """</pre><pre style="
                font-family:Monaco,monospace;
                font-size:14px;color:blue">%s</pre>
               <pre style="
                font-family:Monaco,monospace;
                font-size:14px;">""" % line.lstrip(MESSAGE_MARKER)
            self.request.response.write(line)
            self.request.response.flush()
        self.request.response.write(""" </pre></body></html> """)
        self.request.response.flush()
        return self.request.response

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
