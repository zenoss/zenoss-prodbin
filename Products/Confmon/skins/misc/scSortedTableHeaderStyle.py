## Script (Python) "scSortedTableHeaderStyle"
##parameters=tableName,fieldName,style
##bind context=context
##title=Make a tag for a table header that allows sorting

request = context.REQUEST
session = request.SESSION

if session.has_key(tableName):
    sortedTableState = session[tableName]
    sortedHeader = sortedTableState['sortedHeader']
    if sortedHeader == fieldName:
        style = style + "selected"

return style
