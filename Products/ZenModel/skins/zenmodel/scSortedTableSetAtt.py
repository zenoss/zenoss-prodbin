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
## Script (Python) "scSortedTableSetAtt"
##parameters=tableName,attrib,value=None
##bind context=context
##title=Return a value from a tables current session informtion

request=context.REQUEST
session=request.SESSION
if session.has_key(tableName):
    sortedTableState = session[tableName]
else:
    sortedTableState = {
        'sortedSence' : 'asc',
        'start' : 0,
        'url' : request.URL,
        'sortedHeader' : 'primarySortKey',
        'sortRule' : 'cmp',
        'batchSize' : 20,
        }

if not sortedTableState.has_key(attrib):
    sortedTableState[attrib] = value
if request.has_key(attrib):
    sortedTableState[attrib] = request[attrib]
session[tableName] = sortedTableState

return sortedTableState[attrib]	
