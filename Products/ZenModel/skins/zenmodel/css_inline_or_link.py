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
## Script (Python) "css_inline_or_link"
##parameters=
##bind container=container
##bind context=context
##bind namespace=_
##bind script=script
##bind subpath=traverse_subpath
##title=Browser detection for stylesheet handling

import string

stylesheet_code = ''

if hasattr(context, 'stylesheet_properties'):
    ag = context.REQUEST.get('HTTP_USER_AGENT', '')
    do_inline_css = 1
    sheet = context.stylesheet_properties.select_stylesheet_id

    if sheet:
        if ag[:9] == 'Mozilla/4' and string.find(ag, 'MSIE') < 0:
            s_obj = getattr(context, sheet)
            s_content = s_obj(None, _, do_inline_css=1)
            stylesheet_code = '<style type="text/css">\n<!--\n %s\n -->\n</style>' % s_content
        else:
            server_url = context.absolute_url()
            #took use of portal_url out because its in CMFDefault
            #s_url = '%s/%s' % (context.portal_url(), sheet)
            s_url = '%s/%s' % (server_url, sheet)
            stylesheet_code = '<link rel="stylesheet" href="%s" type="text/css" />' % s_url
return stylesheet_code
