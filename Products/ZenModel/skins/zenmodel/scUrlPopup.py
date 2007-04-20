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
##parameters=tableName,selectname,sessionname,contents,url=None
##bind context=context
##title=build a popup from an array of tuples in the form (name, value)

sesskey = sessionname.split(':')[0]
currentvalue = context.ZenTableManager.getTableState(tableName, sesskey)
select = "<select class='tableheader' name='%s'\n" % (
                                            selectname)
select +=" onchange='document.location.href=this[this.selectedIndex].value'"
select += ">\n"
if not url: url = context.absolute_url_path()
for selname, selval in contents:
    select += "<option value='%s?tableName=%s&%s=%d'" % (
                url, tableName, sessionname, selval)
    if currentvalue == selval:
        select += " selected"
    select += ">%s</options>\n" % selname
select += "</select>"
return select

