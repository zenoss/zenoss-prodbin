#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
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
        self.addColumn('getProductPath')
        self.addColumn('getManufacturer')
        self.addColumn('getProductDescr')


    def getClassifierEntry(self, deviceInfo, log=None):
        """go and classify this device
        deviceInfo is a dictionary with the following keys
            devicename
            community string
            optionally agent port
        """
        snmpdata = self.getDeviceSnmpInfo(deviceInfo, log)
        if snmpdata:
            if log: log.debug('got snmp data: %s' % snmpdata)
            query = self.buildQuery(snmpdata)
            if log: log.debug('query string: %s' % query)
            results = self.searchResults({'keywordsIdx' : query})
            if log: log.debug('got %d classifer enteries' % len(results))
            if results:
                cle = results[0]
                if log:
                    log.debug('DeviceClass Path = %s' 
                                % cle.getDeviceClassPath)
                return cle 

   
    def buildQuery(self, snmpInfo):
        """make query a series of or statements"""
        return " or ".join(snmpInfo.split())


    def getDeviceSnmpInfo(self, deviceInfo, log=None):
        """get the snmp information from the device based on our oid"""
        port = deviceInfo.has_key('port') and deviceInfo['port'] or 161
        from Products.SnmpCollector.SnmpSession import SnmpSession
        import pysnmp
        try:
            snmpsess = SnmpSession(deviceInfo['devicename'],
                                    community=deviceInfo['community'],
                                    port=port)
            data = snmpsess.get(self.oid)
            return data[self.oid]
        except pysnmp.mapping.udp.error.SnmpOverUdpError:
            if log: 
                log.info('snmp problem with device %s' 
                            % deviceInfo['devicename'])
        except:
            if log: log.exception("problem with device %s" 
                            % deviceInfo['devicename'])


InitializeClass(SnmpClassifier)
