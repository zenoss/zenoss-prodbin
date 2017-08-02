##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__='''
ZEN-28160
Setting default values for E-mail notifications.
'''
import Migrate

class addTalesProperty(Migrate.Step):
    version = Migrate.Version(114, 0, 0)

    def cutover(self, dmd):
        for notif in dmd.NotificationSubscriptions.objectValues():
            if notif.action == "email":
                if not hasattr(notif, 'skipfails'):
                    notif.content['skipfails'] = False
                    notif._p_changed = True

addTalesProperty()
