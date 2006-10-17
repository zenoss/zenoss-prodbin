## Script (Python) "logoutUser"
##parameters=
##bind context=context
##title=Logout User
# Attempt to logout the currently logged in user 

req = context.REQUEST
context.acl_users.resetCredentials(req, req.RESPONSE)
# we want to display logged_out when user is logged in with basic auth
# need to figureout how to do this.
#dest = '/zport/dmd/logged_out'
dest = '/zport/dmd/'
if req.get('HTTP_REFERER') != dest:
    req.RESPONSE.redirect(dest)
return
