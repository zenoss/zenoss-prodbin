##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""Classifier

Organizes classifier subclasses to perform high level classification of 
a device.  Subclasses know how to collect information from a device
and look in their indexes for a ClassifierEntry about the device.

$Id: Classifier.py,v 1.4 2004/03/26 23:58:44 edahl Exp $"""

__version__ = "$Revision: 1.4 $"[11:-2]

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from AccessControl import Permissions as permissions
from Products.ZenModel.ZenossSecurity import MANAGER_ROLE, MANAGE_NOTIFICATION_SUBSCRIPTIONS, MANAGE_TRIGGER, NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE, NOTIFICATION_UPDATE_ROLE, NOTIFICATION_VIEW_ROLE, OWNER_ROLE, TRIGGER_MANAGER_ROLE, TRIGGER_UPDATE_ROLE, TRIGGER_VIEW_ROLE, UPDATE_NOTIFICATION, UPDATE_TRIGGER, VIEW_NOTIFICATION, VIEW_TRIGGER, ZEN_ADD, ZEN_ADMINISTRATORS_EDIT, ZEN_ADMINISTRATORS_VIEW, ZEN_ADMIN_DEVICE, ZEN_CHANGE_ADMIN_OBJECTS, ZEN_CHANGE_ALERTING_RULES, ZEN_CHANGE_DEVICE, ZEN_CHANGE_DEVICE_PRODSTATE, ZEN_CHANGE_EVENT_VIEWS, ZEN_CHANGE_SETTINGS, ZEN_COMMON, ZEN_DEFINE_COMMANDS_EDIT, ZEN_DEFINE_COMMANDS_VIEW, ZEN_DELETE, ZEN_DELETE_DEVICE, ZEN_EDIT_LOCAL_TEMPLATES, ZEN_EDIT_USER, ZEN_EDIT_USERGROUP, ZEN_MAINTENANCE_WINDOW_EDIT, ZEN_MAINTENANCE_WINDOW_VIEW, ZEN_MANAGER_ROLE, ZEN_MANAGE_DEVICE, ZEN_MANAGE_DEVICE_STATUS, ZEN_MANAGE_DMD, ZEN_MANAGE_EVENTMANAGER, ZEN_MANAGE_EVENTS, ZEN_RUN_COMMANDS, ZEN_SEND_EVENTS, ZEN_UPDATE, ZEN_USER_ROLE, ZEN_VIEW, ZEN_VIEW_HISTORY, ZEN_VIEW_MODIFICATIONS, ZEN_ZPROPERTIES_EDIT, ZEN_ZPROPERTIES_VIEW
from OFS.OrderedFolder import OrderedFolder

from ZenModelItem import ZenModelItem

def manage_addClassifier(context, title = None, REQUEST = None):
    """make a device"""
    ce = Classifier('ZenClassifier', title)
    context._setObject(ce.id, ce)
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     


class Classifier(ZenModelItem, OrderedFolder):

    meta_type = 'Classifier'
    
    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'Classifier',
            'meta_type'      : 'Classifier',
            'description'    : """Class to manage product information""",
            'icon'           : 'Classifier_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addClassifier',
            'immediate_view' : 'manageClassifiers',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'manageClassifiers'
                , 'permissions'   : (
                  permissions.view, )
                },
            )
          },
        )
    
    security = ClassSecurityInfo()
    
    def __init__(self, id, title=None):
        self.id = id
        self.title = title
        self.curClassifierEntryId = 0
       

    def classifyDevice(self, deviceName, loginInfo, log=None): 
        """kick off device classification against all classifiers
        will walk down a tree of classifiers until the most specific 
        is found.  Top level classifiers can jump into the tree
        where lower level classifiers will then take over the process
        """
        classifierEntry = None
        for classifier in self.getClassifierValues():
            classifierEntry = classifier.getClassifierEntry(
                                            deviceName, loginInfo,log)
            if classifierEntry: break
        return classifierEntry
      

    def getClassifierValues(self):
        return self.objectValues()


    def getClassifierNames(self):
        """return a list of availible classifiers for entry popup"""
        return self.objectIds()


    def getNextClassifierEntryId(self):
        cid = self.curClassifierEntryId
        self.curClassifierEntryId += 1
        return "ClassifierEntry-" + str(cid)


InitializeClass(Classifier)
