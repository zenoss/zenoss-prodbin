##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import Migrate


class AddDeleteSupportBundleMenu(Migrate.Step):
    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):
        dmd.buildMenus({
            'SupportBundleFiles_list': [
            {
                'action': 'dialog_deleteSupportBundle',
                'description': 'Delete Support Bundle...',
                'id': 'deleteSupportBundle',
                'isdialog': True,
                'ordering': 90.50,
                'permissions': ('Change Device',)
            }]
        })


AddDeleteSupportBundleMenu()

