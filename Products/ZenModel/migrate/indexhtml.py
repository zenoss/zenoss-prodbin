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

__doc__='''

Create an index_html at the root level of zope that redirects to
/zports/dmd/

'''

__version__ = "$Revision$"[11:-2]

import Migrate

class IndexHtml(Migrate.Step):
    version = Migrate.Version(0, 23, 0)

    def cutover(self, dmd):
    	''' Remove index_html and replace with a python script that will
    	    redirect to /zport/dmd/
    	'''
        app = dmd.getPhysicalRoot()
        if app.hasObject('index_html'):
            app._delObject('index_html')
    	from Products.PythonScripts.PythonScript import manage_addPythonScript
    	manage_addPythonScript(app, 'index_html')
    	newIndexHtml = app._getOb('index_html')
    	text = 'container.REQUEST.RESPONSE.redirect("/zport/dmd/")\n'
    	newIndexHtml.ZPythonScript_edit('', text)

IndexHtml()
