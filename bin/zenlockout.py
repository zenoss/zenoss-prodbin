#!/opt/zenoss/bin/python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import sys
import getpass
import Zope2
import transaction

CONF_FILE = os.path.join(os.environ['ZENHOME'], 'etc', 'zope.conf')

Zope2.configure(CONF_FILE)
app = Zope2.app()


locker = getattr(app.acl_users, 'account_locker_plugin')
if not locker:
    print("Account locker plugin is not installed")
    sys.exit(0)

def menu():
    while 1:
        try:
            print(
"""
Account manager: 
1. Reset bad attempts for particular account.
2. Reset bad attempts for all accounts.
3. Exit.
"""
            )
                

            job = raw_input(">>> ")

            if job == '1':
                account = raw_input("Enter username:")
                app._p_jar.sync()
                locker.resetAttempts(account)
                print("\nAttempts reseted for {0}\n".format(account))
                transaction.commit()

            elif job == '2':
                app._p_jar.sync()
                locker.resetAllAccounts()
                print("\nDone!\n")
                transaction.commit()

            elif job == '3':
                sys.exit(0)
            
            else:
                print("\nBad index.\n")
                continue
    
        except KeyboardInterrupt:
            sys.exit(0)
            
        except Exception as e:
            print("\n Error: %s" % e)

            

if __name__ == '__main__':
    menu()
