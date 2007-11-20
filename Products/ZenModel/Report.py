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


class Report(ZenModelRM, ZenPackable):
    """Report object"""
    meta_type = 'Report'

    # this is deprecated don't use!!!
    description = ""

    security = ClassSecurityInfo()

    _relations = ZenPackable._relations

    def __init__(self, id, title = None, text=None, content_type=None):
        ZenModelRM.__init__(self, id);
        self._template = ZopePageTemplate(id, text, content_type)
        self.title = title

    def __call__(self, *args, **kwargs):
        """Return our rendered template not our default page
        """
        if not kwargs.has_key('args'):
            kwargs['args'] = args
        template = self._template.__of__(self)
        return template.pt_render(extra_context={'options': kwargs})


    def ZScriptHTML_tryForm(self, *args, **kwargs):
        """Test form called from ZMI test tab
        """
        return self.__call__(self, args, kwargs)


    def manage_main(self):
        """Return the ZMI edit page of our template not ourself
        """
        template = self._template.__of__(self)
        return template.pt_editForm()
    pt_editForm = manage_main

InitializeClass(Report)
