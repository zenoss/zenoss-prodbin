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
## Script (Python) "logoutUser"
##parameters=
##bind context=context
##title=Logout User
# Attempt to logout the currently logged in user 

req = context.REQUEST
context.acl_users.resetCredentials(req, req.RESPONSE)
# we want to display logged_out when user is logged in with basic auth
# need to figureout how to do this.
#dest = '/zport/dmd/logged_out'
dest = '/zport/dmd/'
if req.get('HTTP_REFERER') != dest:
    req.RESPONSE.redirect(dest)
return

