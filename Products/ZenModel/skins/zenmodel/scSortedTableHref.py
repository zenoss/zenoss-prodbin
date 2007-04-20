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
## Script (Python) "scSortedTableHref"
##parameters=tableName,fieldName,sortRule='cmp',params=None
##bind context=context
##title=Make a tag for a table header that allows sorting

request = context.REQUEST
session = request.SESSION

if session.has_key(tableName):
    sortedTableState = session[tableName]
    sortedHeader = sortedTableState['sortedHeader']
    sortedSence = sortedTableState['sortedSence']
    if sortedHeader == fieldName:
        if sortedSence == 'asc':
            sortedSence = 'desc'
        elif sortedSence == 'desc':
            fieldName = ''
            sortedSence = ''
    else:
        sortedSence = 'asc'

    tag = ("%s?tableName=%s&sortedHeader=%s&sortedSence=%s&sortRule=%s%s" 
            % (request.URL,tableName, fieldName, sortedSence, sortRule,params))
    return tag
else:
    raise "SortedTableSessionError", \
            "Can't find %s tableinfo in session" % tableName
