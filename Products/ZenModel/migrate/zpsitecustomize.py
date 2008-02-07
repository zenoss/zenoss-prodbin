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

'''
import Globals
import Migrate
from Products.ZenUtils.Utils import zenPath

class zpSiteCustomize(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
        path = zenPath('lib', 'python', 'sitecustomize.py')
        f = open(path, 'r')
        t = f.read()
        f.close()
        f = open(path, 'w')
        f.write(t)
        f.write('\nimport os, os.path, site; ')
        f.write("site.addsitedir(os.path.join(os.getenv('ZENHOME'), 'ZenPacks'))\n")
        f.close()

zpSiteCustomize()
