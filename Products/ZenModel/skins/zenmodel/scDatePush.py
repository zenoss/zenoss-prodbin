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
## Script (Python) "datePush"
##parameters=tagname,defaultDate=None
##bind context=context
##title=Convert the date popup back to a DateTime

import DateTime

request=context.REQUEST
yr = tagname + "_yr"
mo = tagname + "_mo"
dd = tagname + "_dd"
y=request.get(yr,None)
if y:
    m=request.get(mo)
    d=request.get(dd)
    if y and m and d:
        datestring = "%4d/%02d/%02d" % (y, m, d)
        return DateTime.DateTime(datestring)
else:
    return defaultDate

