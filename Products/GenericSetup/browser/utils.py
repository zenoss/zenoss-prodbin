##############################################################################
#
# Copyright (c) 2005 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""GenericSetup browser view utils.

$Id: utils.py 40715 2005-12-12 10:33:40Z yuppie $
"""

class AddWithPresettingsViewBase:

    """Base class for add views with selectable presettings.
    """

    def title(self):
        return u'Add %s' % self.klass.meta_type

    def __call__(self, add_input_name='', settings_id='', submit_add=''):
        if submit_add:
            obj = self.klass('temp')
            if settings_id:
                ids = settings_id.split('/')
                profile_id = ids[0]
                obj_path = ids[1:]
                if not add_input_name:
                    self.request.set('add_input_name', obj_path[-1])
                self._initSettings(obj, profile_id, obj_path)
            self.context.add(obj)
            self.request.response.redirect(self.context.nextURL())
            return ''
        return self.index()
