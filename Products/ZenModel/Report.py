###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""Report

Report represents a group of devices

$Id: Report.py,v 1.3 2004/04/06 02:19:04 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

from urllib import quote

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable

def manage_addReport(context, id, title = None, text=None,
                    REQUEST = None, submit=None):
    """make a Report"""
    id = str(id)
    if REQUEST is None:
        context._setObject(id, Report(id, text))
        ob = getattr(context, id)
        if title:
            ob.pt_setTitle(title)
        return ob
    else:
        file = REQUEST.form.get('file')
        headers = getattr(file, 'headers', None)
        if headers is None or not file.filename:
            zpt = Report(id)
        else:
            zpt = Report(id, file, headers.get('content_type'))

        context._setObject(id, zpt)

        try:
            u = context.DestinationURL()
        except AttributeError:
            u = REQUEST['URL1']

        if submit == " Add and Edit ":
            u = "%s/%s" % (u, quote(id))
        REQUEST.RESPONSE.redirect(u+'/manage_main')
    return '' 


addReport = PageTemplateFile('www/reportAdd', globals(),
                            __name__='addReport')


class Report(ZopePageTemplate, ZenModelRM, ZenPackable):
    """Report object"""
    meta_type = 'Report'

    # this is deprecated don't use!!!
    description = ""

    security = ClassSecurityInfo()

    _relations = ZenPackable._relations

    pt_editForm = PageTemplateFile('www/reportEdit', globals(),
                                   __name__='pt_editForm')
                                  

    def __init__(self, id, title = None, text=None, content_type=None):
        ZenModelRM.__init__(self, id);
        ZopePageTemplate.__init__(self, id, text, content_type)
        self.title = title

    
    def om_icons(self):
        """Return a list of icon URLs to be displayed by an ObjectManager"""
        icons = ({'path': 'misc_/Confmon/Report_icon.gif',
                  'alt': self.meta_type, 'title': self.meta_type},)
        if not self._v_cooked:
            self._cook()
        if self._v_errors:
            icons = icons + ({'path': 'misc_/PageTemplates/exclamation.gif',
                              'alt': 'Error',
                              'title': 'This template has an error'},)
        return icons


InitializeClass(Report)
