###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import types
import logging
log = logging.getLogger("zen.Events")

from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo

from EventManagerBase import EventManagerBase
from MySqlSendEvent import MySqlSendEventMixin
from Exceptions import *
from Products.Zuul.decorators import deprecated

def manage_addMySqlEventManager(context, id=None, evthost="localhost",
                                evtuser="root", evtpass="", evtdb="events",
                                evtport=3306,
                                history=False, REQUEST=None):
    '''make an MySqlEventManager'''
    if not id:
        id = "ZenEventManager"
        if history: id = "ZenEventHistory"
    evtmgr = MySqlEventManager(id, hostname=evthost, username=evtuser,
                               password=evtpass, database=evtdb,
                               port=evtport)
    context._setObject(id, evtmgr)
    evtmgr = context._getOb(id)
    evtmgr.buildRelations()
    try:
        evtmgr.manage_refreshConversions()
    except:
        log.warn("Failed to refresh conversions, db connection failed.")
    if history:
        evtmgr.defaultOrderby="%s desc" % evtmgr.lastTimeField
        evtmgr.timeout = 300
        evtmgr.statusTable = "history"
    evtmgr.installIntoPortal()
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')


addMySqlEventManager = DTMLFile('dtml/addMySqlEventManager',globals())


class MySqlEventManager(MySqlSendEventMixin, EventManagerBase):

    portal_type = meta_type = 'MySqlEventManager'

    backend = "mysql"

    security = ClassSecurityInfo()

InitializeClass(MySqlEventManager)

