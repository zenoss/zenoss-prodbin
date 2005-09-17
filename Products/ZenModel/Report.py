#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

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

from ZenModelItem import ZenModelItem

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


class Report(ZopePageTemplate, ZenModelItem):
    """Report object"""
    meta_type = 'Report'

    security = ClassSecurityInfo()

    _properties = ZopePageTemplate._properties + (
                    {'id':'description', 'type':'text', 'mode':'w'},
                   ) 

    
    pt_editForm = PageTemplateFile('www/reportEdit', globals(),
                                   __name__='pt_editForm')
                                  

    def __init__(self, id, title = None, text=None, content_type=None,
                        description = ''):
        ZopePageTemplate.__init__(self, id, text, content_type)
        self.title = title
        self.description = description

    
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
