#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

"""DmdNcoManager

Extention of NcoManager to allow DMD specific queries to run
against omnibus

$Id: DmdNcoManager.py,v 1.4 2004/04/22 17:21:16 edahl Exp $"""

__version__ = "$Revision: 1.4 $"[11:-2]

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from NcoManager import NcoManager

def manage_addDmdNcoManager(context, id="", REQUEST = None):
    """make a DmdNcoManager"""
    if not id: id = "netcool"
    d = DmdNcoManager(id)
    context._setObject(id, d)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

class DmdNcoManager(NcoManager):

    portal_type = meta_type = 'DmdNcoManager'

    security = ClassSecurityInfo()
    security.declareProtected('View','getPingStatus')
    def getPingStatus(self, system=None, device=None):
        """get pingstatus from omnibus for device or system"""
        return self.getOmniStatus(system, device, 
                            where="Class=100 and Severity=5")
    
   
    security.declareProtected('View','getSnmpStatus')
    def getSnmpStatus(self, system=None, device=None):
        """get snmpstatus from omnibus for device or system"""
        return self.getOmniStatus(system, device, 
                            where="Agent='SnmpMonitor' and Severity>2")
   

    security.declareProtected('View','getEventCount')
    def getEventCount(self, system=None, device=None):
        """get snmpstatus from omnibus for device or system"""
        return self.getOmniStatus(system, device, 
                            where="Severity>1")
   

    security.declareProtected('View','getOmniStatus')
    def getOmniStatus(self, systemName=None, device=None, where=None):
        """get status from omnibus for device or system"""
        select = "select Node, System, Tally from status where " + where + ";"
        statusCache = self.checkCache(select)
        if not statusCache:
            curs = self._getCursor()
            curs.execute(select)
            nodes={}
            systems=[]
            sysdict={}
            for node, system, tally in curs.fetchall():
                nodes[node[:-1]] = tally
                system = system[:-1]
                tsyses = system.split('|')
                for sys in tsyses:
                    if not sysdict.has_key(sys):
                        sysdict[sys] = 0
                    sysdict[sys] += 1
            for key, value in sysdict.items():
                systems.append((key, value))
            statusCache = (systems, nodes)
            self.addToCache(select,statusCache)
            self._closeDb()
        if device: 
            if statusCache[1].has_key(device):
                return statusCache[1][device]
            else:
                return 0
        if systemName:
            tdown = 0
            systarget = systemName.split('/')[1:]
            for sys, down in statusCache[0]:
                sysar = sys.split('/')[1:]
                if len(systarget) > len(sysar): continue
                match = 1
                for i in range(len(systarget)):
                    if systarget[i] != sysar[i]:
                        match = 0
                        break
                if match: tdown += down
            return tdown
        

InitializeClass(NcoManager)
