##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
from zope.interface import implements
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from ZenModelRM import ZenModelRM
from .interfaces import IAuthorization

def manage_addAuthorization(context):
    """
    Add a new authorization object.
    """
    context._setObject('authorization', Authorization('authorization'))

class Authorization(ZenModelRM):
    """
    """
    implements(IAuthorization)
    
    meta_type = 'Authorization'
    security = ClassSecurityInfo()

    def __init__(self, id):
        ZenModelRM.__init__(self, id);

InitializeClass(Authorization)
