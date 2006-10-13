## Script (Python) "isUserLoggedOut"
##parameters=
##bind context=context
##title=Logout User
# Attempt to logout the currently logged in user 

userName = context.ZenUsers.getUser()

if userName == 'Anonymous User':
    return 'True'
else:
    return 'False'
