###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
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
    
    def getEventSummary(self, where="", severity=1, state=1, prodState=None,
                        parameterizedWhere=None):
        """
        Return a list of tuples with the CSS class, acknowledged count, count

        [['zenevents_5', 0, 3], ...]

        select severity, count(*), group_concat(eventState), 
            from status where device="win2k.confmon.loc" 
            and eventState < 2 group by severity desc;
        """ 
        select = "select severity, count(*), group_concat(eventState) "
        select += "from %s where " % self.statusTable

        paramValues = []
        def paramWhereAnd(where, fmt, field, value):
            log.debug("where is %s" % where)
            if value != None and where.find(field) == -1:
                if where: where += " and "
                where += fmt % (field,)
                paramValues.append(value)
            return where
        where = self.restrictedUserFilter(where)
        #escape any % in the where clause because of format eval later
        where = where.replace('%', '%%')
        if parameterizedWhere is not None:
            pwhere, pvals = parameterizedWhere
            if where: where += " and "
            where += pwhere
            paramValues.extend(pvals)
        where = paramWhereAnd(where, "%s >= %%s", self.severityField, severity)
        where = paramWhereAnd(where, "%s <= %%s", self.stateField, state)
        if prodState is not None:
            where = paramWhereAnd(where, "%s >= %%s", 'prodState', prodState)
        select += where
        select += " group by severity desc"
        #print select
        sevsum = self.checkCache(select)
        if sevsum: return sevsum
        zem = self.dmd.ZenEventManager
        conn = zem.connect()
        try:
            curs = conn.cursor()
            curs.execute(select, paramValues)
            sumdata = {}
            for row in curs.fetchall():
                sev, count, acks = row[:3]
                if hasattr(acks, 'tostring'):
                    acks = acks.tostring()
                if type(acks) in types.StringTypes:
                    acks = acks.split(",")
                ackcount = sum([int(n) for n in acks if n.strip()])
                sumdata[sev] = (ackcount, count)
            sevsum = []
            for name, value in self.getSeverities():
                if value < severity: continue
                css = self.getEventCssClass(value)
                ackcount, count = sumdata.get(value, [0,0])
                sevsum.append([css, ackcount, int(count)])
        finally: zem.close(conn)
        
        self.addToCache(select, sevsum)
        self.cleanCache()
        return sevsum

    def countEventsSince(self, since):
        ''' since is number of seconds since epoch, see documentation
        for python time.time()
        '''
        count = 0
        zem = self.dmd.ZenEventManager
        conn = zem.connect()
        try:
            curs = conn.cursor()
            for table in ('status', 'history'):
                curs.execute('select count(*) from %s where firstTime >= %s' %
                             (table, since))
                count += curs.fetchall()[0][0]
        finally: zem.close(conn)
        return count

InitializeClass(MySqlEventManager)

