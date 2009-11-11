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
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


class PageTemplateMacros(BrowserView):

    template_mappings = {
        'page1':              ('../../ZenModel/skins/zenmodel/templates.pt',
                               'page1'),
        'page2':              ('../../ZenModel/skins/zenmodel/templates.pt',
                               'page2'),
        'base':               ('templates/base.pt',
                               'base'),
        'base-new':           ('templates/base-new.pt',
                               'base-new'),
        'masterdetail':       ('templates/masterdetail.pt',
                               'masterdetail'),
        'masterdetail-new':   ('templates/masterdetail-new.pt',
                               'masterdetail-new'),
        'masterdetailsplit2': ('templates/masterdetailsplit2.pt',
                               'masterdetailsplit2'),
        'masterdetailsplit3': ('templates/masterdetailsplit3.pt',
                               'masterdetailsplit3'),
        'masterdetailnested': ('templates/masterdetailnested.pt',
                               'masterdetailnested'),
        'verticalbrowse':     ('templates/verticalbrowse.pt',
                               'verticalbrowse')
    }

    def __getitem__(self, key):
        template, macro = self.template_mappings[key]
        return ViewPageTemplateFile(template).macros[macro]



class BBBMacros(BrowserView):
    def __getitem__(self, key):
        if key=='macros':
            return self
        tpl = ViewPageTemplateFile(
            '../../ZenModel/skins/zenmodel/templates.pt')
        return tpl.macros[key]

