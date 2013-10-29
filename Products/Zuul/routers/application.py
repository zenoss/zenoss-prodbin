##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging
from Products.ZenMessaging.audit import audit
from Products.Zuul.routers import TreeRouter
from Products.ZenUtils.Ext import DirectResponse
from Products.Zuul.interfaces import IInfo
from Products import Zuul


log = logging.getLogger('zen.ApplicationRouter')


class ApplicationRouter(TreeRouter):


    def _getFacade(self):
        return Zuul.getFacade('applications', self.context)

    def getTree(self, id):
        """
        Returns the tree structure of the application (service) hierarchy where
        the root node is the organizer identified by the id parameter.

        @type  id: string
        @param id: Id of the root node of the tree to be returned
        @rtype:   [dictionary]
        @return:  Object representing the tree
        """
        facade = self._getFacade()
        applications = facade.query()
        infos = map(IInfo, applications)
        data = Zuul.marshal(infos)
        return data

    def start(self, uids):
        """
        Will issue the command to start the selected ids
        @type uids: Array[Strings]
        @param uids: List of valid daemon ids that will need to started
        @rtype: DirectResposne
        @return: DirectReponse of success if no errors are encountered
        """
        facade = self._getFacade()
        applications = facade.query()
        for app in applications:
            if app.id in uids:
                app.start()
                audit('UI.Applications.Start', id)
        return DirectResponse.succeed("Started %s" % ",".join(uids))

    def stop(self, uids):
        """
        Will issue the command to stop the selected ids
        @type uids: Array[Strings]
        @param uids: List of valid daemon ids that will need to stopped
        @rtype: DirectResposne
        @return: DirectReponse of success if no errors are encountered
        """
        facade = self._getFacade()
        applications = facade.query()
        for app in applications:
            if app.id in uids:
                app.stop()
                audit('UI.Applications.Stop', id)
        return DirectResponse.succeed("Stopped %s" % ",".join(uids))

    def restart(self, uids):
        """
        Will issue the command to restart the selected ids
        @type uids: Array[Strings]
        @param uids: List of valid daemon ids that will need to restarted
        @rtype: DirectResposne
        @return: DirectReponse of success if no errors are encountered
        """
        facade = self._getFacade()
        applications = facade.query()
        for app in applications:
            if app.id in uids:
                app.restart()
                audit('UI.Applications.Restart', id)
        return DirectResponse.succeed("Restarted %s" % ",".join(uids))

    def getInfo(self, id):
        """
        Returns the serialized info object for the given id
        @type: id: String
        @param id: Valid id of a application
        @rtype: DirectResponse
        @return: DirectResponse with data of the application
        """
        facade = self._getFacade()
        info = facade.get(id)
        data = Zuul.marshal(IInfo(info))
        return DirectResponse.succeed(data=data)
