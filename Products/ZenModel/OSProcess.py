##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from Products.ZenModel.ZenossSecurity import *
from Products.ZenModel.Lockable import Lockable
from Commandable import Commandable
from Products.ZenRelations.RelSchema import *
from Products.ZenWidgets import messaging
from Acquisition import aq_chain
from Lockable import UNLOCKED, DELETE_LOCKED, UPDATE_LOCKED
from OSComponent import OSComponent
from ZenPackable import ZenPackable
from Products.ZenUtils.Utils import prepId
import logging
import re

log = logging.getLogger("zen.osprocess")

def manage_addOSProcess(context, newClassName, userCreated, REQUEST=None):
    """
    Make an os process from the ZMI
    """
    id = newClassName.split('/')[-1]
    osp = OSProcess(id)
    # Indexing is subscribed to ObjectAddedEvent, which fires
    # on _setObject, so we want to set process class first.
    osp.__of__(context).setOSProcessClass(newClassName)
    context._setObject(id, osp)
    osp = context._getOb(id)
    osp.processText = id
    if userCreated: osp.setUserCreateFlag()
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
    return osp


def createFromObjectMap(context, objectMap):
    # invoked from Products/DataCollector/ProcessCommandPlugin.py
    om = objectMap
    processes = context.device().getDmdRoot("Processes")
    pcs = processes.getSubOSProcessClassesSorted()

    for pc in pcs:
        if OSProcess.matchRegex(re.compile(pc.regex), re.compile(pc.excludeRegex), om.processText):
            uniqueId = OSProcess.generateId(re.compile(pc.regex), pc.getPrimaryUrlPath(), om.processText)
            
            result = OSProcess(uniqueId)
            om.setOSProcessClass = pc.getPrimaryDmdId()
            om.id = uniqueId

            return result


class OSProcess(OSComponent, Commandable, ZenPackable):
    """
    OSProcess object
    """
    portal_type = meta_type = 'OSProcess'

    processText = ""
    procName = "" 
    parameters = "" 
    minProcessCount = ""
    maxProcessCount = ""
    _procKey = ""

    modelerLock = None
    sendEventWhenBlockedFlag = None

    collectors = ('zenprocess','zencommand')

    _properties = OSComponent._properties + (
        {'id':'procName', 'type':'string', 'mode':'w'}, 
        {'id':'parameters', 'type':'string', 'mode':'w'}, 
        {'id':'processText', 'type':'string', 'mode':'w'},
        {'id':'zAlertOnRestarts', 'type':'boolean', 'mode':'w'},
        {'id':'zFailSeverity', 'type':'int', 'mode':'w'},
        {'id':'minProcessCount', 'type':'int', 'mode':'w'},
        {'id':'maxProcessCount', 'type':'int', 'mode':'w'},
    )

    _relations = OSComponent._relations + ZenPackable._relations + (
        ("os", ToOne(ToManyCont, "Products.ZenModel.OperatingSystem", "processes")),
        ("osProcessClass", ToOne(ToMany, "Products.ZenModel.OSProcessClass", "instances")),
        ('userCommands', ToManyCont(ToOne, 'Products.ZenModel.UserCommand', 'commandable')),
    )

    factory_type_information = (
        {
            'immediate_view' : 'osProcessDetail',
            'actions'        :
            (
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'osProcessDetail'
                , 'permissions'   : ( Permissions.view, )
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (ZEN_VIEW, )
                },
                { 'id'            : 'perfConf'
                , 'name'          : 'Template'
                , 'action'        : 'objTemplates'
                , 'permissions'   : ("Change Device", )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'osProcessManage'
                , 'permissions'   : ("Manage DMD",)
                },
            )
         },
        )

    security = ClassSecurityInfo()


    @staticmethod
    def extractNameCaptureGroups(groups):
        name_captured_groups = ""
        if isinstance(groups[0], basestring):
            return prepId(groups[0])
        else:
            for group in groups[0]:
                name_captured_groups = name_captured_groups + "_" + prepId(group)
            
            return name_captured_groups[1:]


    @staticmethod
    def generateId(searchRegex, primaryURLPath, processText):
        """
        Generate a unique ID based on the primaryURLPath AND any name capture groups
        
        @parameter searchRegex: regex to search the name_with_args for
        @type searchRegex: regex
        @parameter primaryURLPath: url path
        @type primaryURLPath:: string
        @parameter processText: name of a process to compare (includes args)
        @type processText: string
        @return: uniqueId based on the primaryURLPath + name capture groups (if any are present)
        @rtype: string
        """
        preparedId = prepId(primaryURLPath)

        if searchRegex.groups is not 0:
            name_captured_groups = OSProcess.extractNameCaptureGroups( searchRegex.findall(processText) )
            log.debug("generateId's name_captured_groups: %s" % name_captured_groups)
            preparedId = preparedId + "_" + name_captured_groups
        
        log.debug("Generated unique ID: %s" % preparedId)
        return preparedId


    @staticmethod
    def matchRegex(searchRegex, excludeRegex, name_with_args):
        """
        Perform exact comparisons on the process names.
        
        @parameter searchRegex: regex to search the name_with_args for
        @type searchRegex:: regex
        @parameter excludeRegex: regex to search the name_with_args for and return False if anything is found
        @type excludeRegex:: regex
        @parameter name_with_args: name of a process to compare (includes args)
        @type name_with_args:: string
        @return: does the name match this process's info?
        @rtype: Boolean
        """
        # search for the regex we are looking for
        if searchRegex.search(name_with_args) is not None:
            # ensure the excluded regex does NOT apply
            if excludeRegex.search(name_with_args) is None:
                return True
            else:
                log.debug("Rejecting %s due to exclude regex" % name_with_args)

        # return False if the search regex is NOT found ... or ... if the excluded regex IS found
        return False


    @staticmethod
    def matchNameCaptureGroups(searchRegex, name_with_args, originalId):
        """
        if there are 0 name capture groups in the searchRegex, return True
        if there is at least 1 name capture group in the searchRegex, return True ONLY if the
            name capure group match matches with the suffix of the originalId
        
        @parameter searchRegex: regex to search the name_with_args for
        @type searchRegex:: regex
        @parameter name_with_args: name of a process to compare (includes args)
        @type name_with_args:: string
        @parameter originalId: componentID determined at model time
        @type originalId:: string
        @return: 
        @rtype: Boolean
        """
        # no name capture groups!
        if searchRegex.groups is 0:
            log.debug("Found: %s to be a member of %s" % (name_with_args, originalId))
            return True
        
        # at least one name capture groups...
        else:
            # Return all non-overlapping matches
            name_captured_groups = OSProcess.extractNameCaptureGroups( searchRegex.findall(name_with_args) )

            # example originalId: zport_dmd_Processes_osProcessClasses_capturing_groups_myapp
            # search at the END of the originalId (produced during modeling)
            name_capture_groups_regex = re.compile(name_captured_groups + "$")
            if name_capture_groups_regex.search(str(originalId)) is not None:
                log.debug("Found: %s to be a member of %s" % (name_with_args, originalId))
                return True

        return False


    def getOSProcessConf(self):
        """
        Return information used to monitor this process.
        """
        return (self.id, self.alertOnRestart(), self.getFailSeverity())


    def setOSProcessClass(self, procKey):
        """
        Set the OSProcessClass based on procKey which is the proc + args.
        We set by matching regular expressions of each proces class.
        """
        klass = self.getDmdObj(procKey)
        klass.instances.addRelation(self)


    def getOSProcessClass(self):
        """
        Return the current procKey.
        """
        pClass = self.osProcessClass()
        if pClass:
            return pClass.getPrimaryDmdId()


    def getOSProcessClassLink(self):
        """
        Return an a link to the OSProcessClass.
        """
        proccl = self.osProcessClass()
        if proccl:
            if self.checkRemotePerm("View", proccl):
                return "<a href='%s'>%s</a>" % (proccl.getPrimaryUrlPath(),
                                                proccl.getOSProcessClassName())
            else:
                return proccl.getOSProcessClassName()
        return ""

    def getMinProcessCount(self):
        """
        Return the min process count threshold value
        """
        if not self.minProcessCount and not self.maxProcessCount and \
           self.osProcessClass():
            value = self.osProcessClass().minProcessCount
        else:
            value = self.minProcessCount

        return float(value or '0')

    def getMaxProcessCount(self):
        """
        Return the max process count threshold value
        """
        if not self.minProcessCount and not self.maxProcessCount and \
           self.osProcessClass():
            value = self.osProcessClass().maxProcessCount
        else:
            value = self.maxProcessCount

        return float(value or 'nan')

    def name(self):
        """
        Return a string that is the process text (process name + parameters)
        """
        return self.processText

    title = name


    def monitored(self):
        """
        Should this service be monitored or not. Use ServiceClass aq path.
        """
        return self.getAqProperty("zMonitor")


    def alertOnRestart(self):
        """
        Retrieve the zProperty zAlertOnRestart
        """
        return self.getAqProperty("zAlertOnRestart")


    def getSeverities(self):
        """
        Return a list of tuples with the possible severities
        """
        return self.ZenEventManager.getSeverities()


    def getFailSeverity(self):
        """
        Return the severity for this service when it fails.
        """
        return self.getAqProperty("zFailSeverity")


    def getFailSeverityString(self):
        """
        Return a string representation of zFailSeverity
        """
        return self.ZenEventManager.severities[self.getAqProperty("zFailSeverity")]


    def getClassObject(self):
        """
        Return the ProcessClass for this proc
        """
        return self.osProcessClass()


    security.declareProtected('Manage DMD', 'manage_editOSProcess')
    def manage_editOSProcess(self, zMonitor=False, zAlertOnRestart=False,
                             zFailSeverity=3, msg=None,REQUEST=None):
        """
        Edit a Service from a web page.
        """
        if msg is None: msg=[]
        msg.append(self.setAqProperty("zMonitor", zMonitor, "boolean"))
        msg.append(self.setAqProperty("zAlertOnRestart",zAlertOnRestart,"int"))
        msg.append(self.setAqProperty("zFailSeverity",zFailSeverity,"int"))
        msg = [ m for m in msg if m ]
        self.index_object()
        if not msg: msg.append("No action needed")
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Process Edited',
                ", ".join(msg) + ":"
            )
            return self.callZenScreen(REQUEST)


    def getUserCommandTargets(self):
        '''
        Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        '''
        return [self]


    def getUserCommandEnvironment(self):
        """
        Return the environment to be used when processing a UserCommand
        """
        environ = Commandable.getUserCommandEnvironment(self)
        context = self.primaryAq()
        environ.update({'proc': context,  'process': context,})
        return environ


    def getAqChainForUserCommands(self):
        """
        Setup the aq chain as appropriate for the execution of a UserCommand
        """
        chain = aq_chain(self.getClassObject().primaryAq())
        chain.insert(0, self)
        return chain


    def getUrlForUserCommands(self):
        """
        Return the url where UserCommands are viewed for this object
        """
        return self.getPrimaryUrlPath() + '/osProcessManage'

    # override the lock methods to look for the process classes'
    # lock state instead of the current object if it has not been set

    def _getSendEventWhenBlockedFlag(self):
        if self.sendEventWhenBlockedFlag is None and self.osProcessClass():
            return self.osProcessClass().getZ("zSendEventWhenBlockedFlag")
        return self.sendEventWhenBlockedFlag

    def sendEventWhenBlocked(self):
        return self._getSendEventWhenBlockedFlag()

    def _getModelerLock(self):
        if self.modelerLock is None and self.osProcessClass():
            return self.osProcessClass().getZ("zModelerLock")
        return self.modelerLock

    def isUnlocked(self):
        return self._getModelerLock() == UNLOCKED

    def isLockedFromDeletion(self):
        lock = self._getModelerLock()
        return (lock == DELETE_LOCKED
                or lock == UPDATE_LOCKED)

    def isLockedFromUpdates(self):
        return self._getModelerLock() == UPDATE_LOCKED

    def _checkLockProperties(self):
        """
        If we are reseting the locking properties of a process
        to the same as the class then delete the local copy.

        This means that if you override a process instance to have
        a locking policy different then its parent, but then change your
        mind and reset it to the parents it will update with the parents.
        """
        if self.osProcessClass():
            pclass = self.osProcessClass()
            if pclass.getZ("zModelerLock") == self.modelerLock:
                self.modelerLock = None
                # if they reset the modeler lock see if we can reset the
                # send flag as well
                if pclass.getZ("zSendEventWhenBlockedFlag") == self.sendEventWhenBlockedFlag:
                    self.sendEventWhenBlockedFlag = None

    def unlock(self, REQUEST=None):
        Lockable.unlock(self, REQUEST=REQUEST)
        self._checkLockProperties()

    def lockFromDeletion(self, sendEventWhenBlocked=None, REQUEST=None):
        Lockable.lockFromDeletion(self, sendEventWhenBlocked=sendEventWhenBlocked, REQUEST=REQUEST)
        self._checkLockProperties()

    def lockFromUpdates(self, sendEventWhenBlocked=None, REQUEST=None):
        Lockable.lockFromUpdates(self, sendEventWhenBlocked=sendEventWhenBlocked, REQUEST=REQUEST)
        self._checkLockProperties()


InitializeClass(OSProcess)
