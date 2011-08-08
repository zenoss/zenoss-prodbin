###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import Migrate

from Products.ZenUtils.Security import setupSessionHelper, setupCookieHelper


class SessionAuthentication(Migrate.Step):
    version = Migrate.Version(4, 0, 0)

    def __init__(self):
        Migrate.Step.__init__(self)

    def cutover(self, dmd):
        zport = dmd.zport
        app = zport.unrestrictedTraverse('/')
        # set up dmd users
        setupCookieHelper(zport)
        setupSessionHelper(zport)

        # make sure admin is set up correctly
        setupCookieHelper(app)
        setupSessionHelper(app)

SessionAuthentication()

