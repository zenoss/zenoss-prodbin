##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging
from urllib2 import URLError

from Products import Zuul
from Products.ZenMessaging.audit import audit
from Products.Zuul.routers import TreeRouter
from Products.ZenUtils.Ext import DirectResponse
from Products.Zuul.form.interfaces import IFormBuilder
from Products.Zuul.interfaces import IInfo, ITreeNode

log = logging.getLogger('zen.ApplicationRouter')


class ApplicationRouter(TreeRouter):
    """
    """

    def _getFacade(self):
        return Zuul.getFacade('applications', self.context)

    def getTree(self, id):
        """
        Returns the tree structure of the application and collector
        hierarchy.

        @type  id: string
        @param id: Id of the root node of the tree to be returned
        @rtype:   [dictionary]
        @return:  Object representing the tree
        """
        try:
            appfacade = self._getFacade()
            monitorfacade = Zuul.getFacade("monitors", self.context)
            nodes = [ITreeNode(m) for m in monitorfacade.query()]
            for monitor in nodes:
                apps = appfacade.queryMonitorDaemons(monitor.name)
                for app in apps:
                    monitor.addChild(IInfo(app))
            apps = appfacade.queryMasterDaemons()
            for app in apps:
                nodes.append(IInfo(app))
            return Zuul.marshal(nodes)
        except URLError as e:
            log.exception(e)
            return DirectResponse.fail(
                "Error fetching daemons list: " + str(e.reason)
            )

    def getForm(self, uid):
        """
        Given an object identifier, this returns all of the editable fields
        on that object as well as their ExtJs xtype that one would
        use on a client side form.

        @type  uid: string
        @param uid: Unique identifier of an object
        @rtype:   DirectResponse
        @return:  B{Properties}
           - form: (dictionary) form fields for the object
        """
        app = self._getFacade().get(uid)
        form = IFormBuilder(IInfo(app)).render(fieldsets=False)
        form = Zuul.marshal(form)
        return DirectResponse(form=form)

    def start(self, uids):
        """
        Will issue the command to start the selected ids
        @type uids: Array[Strings]
        @param uids: List of valid daemon ids that will need to started
        @rtype: DirectResposne
        @return: DirectReponse of success if no errors are encountered
        """
        facade = self._getFacade()
        for uid in uids:
            facade.start(uid)
            audit('UI.Applications.Start', id)
        if len(uids) > 1:
            return DirectResponse.succeed("Started %s daemons" % len(uids))
        return DirectResponse.succeed()

    def stop(self, uids):
        """
        Will issue the command to stop the selected ids
        @type uids: Array[Strings]
        @param uids: List of valid daemon ids that will need to stopped
        @rtype: DirectResposne
        @return: DirectReponse of success if no errors are encountered
        """
        facade = self._getFacade()
        for uid in uids:
            facade.stop(uid)
            audit('UI.Applications.Stop', id)
        if len(uids) > 1:
            return DirectResponse.succeed("Stopped %s daemons" % len(uids))
        return DirectResponse.succeed()

    def restart(self, uids):
        """
        Will issue the command to restart the selected ids
        @type uids: Array[Strings]
        @param uids: List of valid daemon ids that will need to restarted
        @rtype: DirectResposne
        @return: DirectReponse of success if no errors are encountered
        """
        facade = self._getFacade()
        for uid in uids:
            facade.restart(uid)
            audit('UI.Applications.Restart', id)
        if len(uids) > 1:
            return DirectResponse.succeed("Restarted %s daemons" % len(uids))
        return DirectResponse.succeed()

    def setAutoStart(self, uids, enabled):
        """
        Enables or disables autostart on all applications passed into uids.
        If it is already in that state it is a noop.
        @type uids: Array[Strings]
        @param uids: List of valid daemon ids that will need to enabled
        @type enabled: boolean
        @param uids: true for enabled or false for disabled
        @rtype: DirectResposne
        @return: DirectReponse of success if no errors are encountered
        """
        facade = self._getFacade()
        applications = facade.query()
        for app in applications:
            if app.id in uids:
                app.autostart = enabled
                audit('UI.Applications.AutoStart', id, {'autostart': enabled})
        return DirectResponse.succeed()

    def getInfo(self, id):
        """
        Returns the serialized info object for the given id
        @type: id: String
        @param id: Valid id of a application
        @rtype: DirectResponse
        @return: DirectResponse with data of the application
        """
        facade = self._getFacade()
        app = facade.get(id)
        data = Zuul.marshal(IInfo(app))
        return DirectResponse.succeed(data=data)

    def getAllResourcePools(self, query=None):
        """
        Returns a list of resource pool identifiers.
        @rtype: DirectResponse
        @return:  B{Properties}:
             - data: ([String]) List of resource pool identifiers
        """
        pools = {'name': 'default'}
        return DirectResponse.succeed(data=Zuul.marshal(pools))    
        
