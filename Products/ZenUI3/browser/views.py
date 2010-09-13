###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

class FileUpload(BrowserView):
    """
    Renders a file upload in an iframe and asks the context to handle the results
    """

    template = ViewPageTemplateFile('./templates/formUpload.pt')
    
    def __call__(self, *args, **kwargs):
        """
        If we are in postback (submit is present) then we save the file.
        """
        if self.isPostBack:
            if self.request.upload.filename:
                self.context.handleUploadedFile(self.request)
        
        return self.template()
    
    @property
    def isPostBack(self):
        return self.request.get('submit')

class Robots(BrowserView):
    """
    Returns a robots.txt
    """

    def __call__(self, *args, **kwargs):
        """
        Return the robots.txt in the resource dir
        """
        import os.path
        with open(os.path.dirname(__file__) +'/resources/txt/robots.txt') as f:
            return f.read()

