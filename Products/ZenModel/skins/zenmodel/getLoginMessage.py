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
