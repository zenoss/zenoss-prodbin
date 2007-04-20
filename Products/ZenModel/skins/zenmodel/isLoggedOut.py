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
## Script (Python) "isUserLoggedOut"
##parameters=
##bind context=context
##title=Logout User
# Attempt to logout the currently logged in user 

userName = context.ZenUsers.getUser()

if userName == 'Anonymous User':
    return 'True'
else:
    return 'False'

