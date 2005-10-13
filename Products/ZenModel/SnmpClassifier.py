#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""SnmpClassifier

Collects snmp data about a device which will be used to classify the device
Instances point the classifier to the oid to be collected.

$Id: SnmpClassifier.py,v 1.9 2003/05/23 17:25:35 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import Persistent
from Globals import InitializeClass

from Products.ZCatalog.ZCatalog import ZCatalog
from Products.ZCTextIndex.ZCTextIndex import manage_addLexicon

from SearchUtils import makeConfmonLexicon, makeIndexExtraParams


def manage_addSnmpClassifier(context, id, title = None, REQUEST = None):
    """make an snmpclassifier and add its lexicon"""
    ce = SnmpClassifier(id, title)
    context._setObject(ce.id, ce)
    ce = context._getOb(ce.id)
    ce._afterInit()

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main')


addSnmpClassifier = DTMLFile('dtml/addSnmpClassifier',globals())


class SnmpClassifier(ZCatalog):
    """classify devices based on snmp information"""

    meta_type = 'SnmpClassifier'

    # use zcatalog for now
    #manage_options = () 
                    
    _properties = ZCatalog._properties + (
                    {'id':'oid', 'type':'string', 'mode':'rw'},
                    )

    security = ClassSecurityInfo()


    def __init__(self, id, title=None, oid=""):
        ZCatalog.__init__(self, id, title)
        self.oid = oid


    def _afterInit(self):
        """Set up the catalog once our aquisition path is ok"""
        makeConfmonLexicon(self)
        self.addIndex('keywordsIdx', 'ZCTextIndex', 
                        extra=makeIndexExtraParams('keywords'))
        self.addIndex('summaryIdx', 'ZCTextIndex', 
                        extra=makeIndexExtraParams('summary'))
        self.addColumn('getDeviceClassPath')
        self.addColumn('getProduct')
        self.addColumn('getManufacturer')
        self.addColumn('getProductDescr')


    def getClassifierEntry(self, deviceName, loginInfo, log=None):
        """go and classify the device named deviceName
        loginInfo is a dictionary which can have the following keys
            snmpCommunity, snmpPort, loginName, loginPassword
        """
        if not log:
            import logging
            log = logging.getLogger()
        snmpdata = self.getDeviceSnmpInfo(deviceName, loginInfo, log)
        if snmpdata:
            log.debug('got snmp data: %s' % snmpdata)
            query = self.buildQuery(snmpdata)
            log.debug('query string: %s' % query)
            results = self.searchResults({'keywordsIdx' : query})
            log.debug('got %d classifer enteries' % len(results))
            if results:
                cle = results[0]
                if log:
                    log.debug('DeviceClass Path = %s' 
                                % cle.getDeviceClassPath)
                return cle 

   
    def buildQuery(self, snmpInfo):
        """make query a series of or statements"""
        return " or ".join(snmpInfo.split())


    def getDeviceSnmpInfo(self, deviceName, loginInfo, log):
        """get the snmp information from the device based on our oid"""
        from Products.SnmpCollector.SnmpSession import SnmpSession
        from Products.SnmpCollector.SnmpCollector import findSnmpCommunity
        devices = self.getDmdRoot("Devices")
        port = loginInfo.get('snmpPort', None)
        if not port: 
            port = getattr(devices, "zSnmpPort", 161)
        community = loginInfo.get("snmpCommunity", None)
        if not community: 
            community = findSnmpCommunity(devices, deviceName, port=port)
        import pysnmp
        try:
            snmpsess = SnmpSession(deviceName, community=community, port=port)
            data = snmpsess.get(self.oid)
            return data[self.oid]
        except pysnmp.mapping.udp.error.SnmpOverUdpError:
            log.info('snmp problem with device %s' % deviceName)
        except (SystemExit, KeyboardInterrupt): raise
        except:
            log.exception("problem with device %s" % deviceName)
                            


InitializeClass(SnmpClassifier)
