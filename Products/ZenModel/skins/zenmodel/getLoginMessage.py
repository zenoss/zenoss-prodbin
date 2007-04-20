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
# This program is part of Zenoss Core, an open source monitoring platform.
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
# For complete information please visit: http://www.zenoss.com/oss/
## Script (Python) "getLoginMessage"
##parameters=
##bind context=context
##title=Logout User
# Attempt to logout the currently logged in user 

req = context.REQUEST
resp = req.RESPONSE

msg = ''
url = req.form.get('came_from') or ''
if 'terms' in url:
    msg = 'You did not accept the<br/>Zenoss Terms.'
elif 'submitted' in url:
    msg = 'The entered password or<br/>username is incorrect.'
return msg

