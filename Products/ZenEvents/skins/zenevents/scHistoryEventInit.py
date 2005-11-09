## Script (Python) "scHistoryEventInit"
##parameters=tableName,defaultSort='primarySortKey',defaultSortRule='cmp',sortedSence='asc'
##bind context=context
##title=setup the session variables for history events

import DateTime

request=context.REQUEST
session=request.SESSION


whereClause = request.get('ev_whereclause', None)
orderby = request.get('ev_orderby', None)
myclear = request.get('clear',0)
sortedTableState = session.get(tableName, None)

if (not sortedTableState
    or not sortedTableState.has_key('whereClause')
    or myclear
    or (whereClause and whereClause != sortedTableState['whereClause'])):
    sortedTableState = {
        'sortedSence' : sortedSence,
        'start' : 0,
        'url' : request.URL,
        'sortedHeader' : defaultSort,
        'sortRule' : defaultSortRule,
        'batchSize' : 20,
        'orderby' : orderby,
        'whereClause' : whereClause,
        }

if request.has_key('start_date_pop_mo'):
    sortedTableState['startdate'] = context.scDatePush(
                                                'start_date_pop',request)
elif not sortedTableState.has_key('startdate'):
    sortedTableState['startdate']=DateTime.DateTime()-1;

if request.has_key('end_date_pop_mo'):
    sortedTableState['enddate'] = context.scDatePush(
                                                'end_date_pop',request)
elif not sortedTableState.has_key('enddate'):
    sortedTableState['enddate']=DateTime.DateTime()

session[tableName] = sortedTableState

return sortedTableState['whereClause']
