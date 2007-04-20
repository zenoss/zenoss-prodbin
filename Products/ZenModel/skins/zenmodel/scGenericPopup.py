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
## Script (Python) "sortedTableNavigation"
##parameters=tableName,selectname,contents
##bind context=context
##title=build a popup from an array of tuples in the form (name, value)

request=context.REQUEST
session=request.SESSION
if session.has_key(tableName):
    sortedTableState = session[tableName]
    currentvalue = sortedTableState.get(selectname.split(':')[0])
    select = "<select class='tableheader' name='%s'\n" % (
                                                selectname)
    select +=" onchange='this.form.submit()'"
    select += ">\n"
    for selname, selval in contents:
        select += "<option value='%s'" % selval
        if currentvalue == selval:
            select += " selected"
        select += ">%s</options>\n" % selname
    select += "</select>"
    return select

