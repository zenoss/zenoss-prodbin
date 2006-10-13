## Script (Python) "logoutUser"
##parameters=
##bind context=context
##title=Logout User
# Attempt to logout the currently logged in user 

req = context.REQUEST
context.acl_users.resetCredentials(req, req.RESPONSE)
dest = '/zport/dmd/logged_out'
if req.get('HTTP_REFERER') != dest:
    req.RESPONSE.redirect(dest)
return
