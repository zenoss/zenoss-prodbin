## Script (Python) "getSortedTableState"
##parameters=tableName,key
##bind context=context
##title=Return a value from a tables current session informtion

request=context.REQUEST
session=request.SESSION
if session.has_key(tableName):
    sortedTableState = session[tableName]
    if sortedTableState.has_key(key):
        return sortedTableState[key]
