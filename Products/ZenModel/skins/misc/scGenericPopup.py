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
