#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""DmdBuilder

DmdBuilder builds out the core containment structure used in the dmd database.

Devices
Groups
Locations
Networks
ServiceAreas
Services
Systems
Companies

$Id: DmdBuilder.py,v 1.40 2004/02/14 19:11:00 edahl Exp $"""

__version__ = "$Revision: 1.40 $"[11:-2]

import sys
import getopt

import Zope
app=Zope.app()
from OFS.Image import File
from Acquisition import aq_base

from Products.ZenModel.CompanyClass import CompanyClass
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.ServerClass import ServerClass
from Products.ZenModel.LocationClass import LocationClass
from Products.ZenModel.GroupClass import GroupClass
from Products.ZenModel.ProductClass import ProductClass
from Products.ZenModel.NetworkClass import NetworkClass
from Products.ZenModel.ServiceAreaClass import ServiceAreaClass
from Products.ZenModel.ServiceClass import ServiceClass
from Products.ZenModel.SystemClass import SystemClass
from Products.ZenModel.MonitorClass import MonitorClass
from Products.ZenModel.RouterClass import RouterClass
from Products.ZenModel.UbrRouterClass import UbrRouterClass
from Products.ZenModel.DataRoot import DataRoot
from Products.ZenRelations.SchemaManager import SchemaManager, manage_addSchemaManager
from Products.ZenModel.Classifier import manage_addClassifier
from Products.ZenModel.SnmpClassifier import manage_addSnmpClassifier
from Products.ZenModel.ZentinelPortal import manage_addZentinelSite
from Products.ZenModel.ZDeviceLoader import ZDeviceLoader

classifications = {
    'Companies':    CompanyClass,
    'Devices':      DeviceClass,
    'Servers':      ServerClass,
    'Groups':       GroupClass,
    'Locations':    LocationClass,
    'Networks':     NetworkClass,
    'Products':     ProductClass,
    'ServiceAreas': ServiceAreaClass,
    'Services':     ServiceClass,
    'Systems':      SystemClass,
    'Monitors':     MonitorClass,
    'Routers':      RouterClass,
    'UbrRouters':   UbrRouterClass,
}

arpSnmpMap = [
    {'id':  'relationshipName', 'value':'arptable', 'type':'string'},
    {'id':  'remoteClass', 'value':'Confmon.ArpEntry', 'type':'string'},
    {'id':  'tableOid', 'value':'.1.3.6.1.2.1.4.22.1', 'type':'string'},
    {'id':  '.2', 'value':      'macAddress', 'type': 'oid'},
    {'id':  '.3', 'value':      'id', 'type':   'oid'},
    ]

class DmdBuilder:

    def _makeObjProps(self, obj, props):
        obj._properties = ()
        for propEntry in props:
            if propEntry['type'] == 'oid':
                # add to object's snmpMap
                obj._oidmap[propEntry['id']] = propEntry['value']
            obj._setProperty(propEntry['id'],propEntry['value'],type=propEntry['type'])
        return obj

    def buildRoots(self, dmd):
        dmdroots = ('Companies', 'Devices', 'Groups', 'Locations', 
                'Networks', 'Products', 'ServiceAreas', 'Services',
                'Systems', 'Monitors')
        self.addroots(dmd, dmdroots)
        dmd.Devices._setProperty('snmp_communities', ['public', 'private'],
                                    type='lines')
    def buildProducts(self, dmd):
        prods = dmd.Products
        prodRoots = ('Hardware','Software')
        self.addroots(prods, prodRoots, "Products")

    def buildMonitors(self, dmd):
        mons = dmd.Monitors
        monRoots = ('StatusMonitors','Cricket')
        self.addroots(mons, monRoots, "Monitors")

    def buildServices(self, dmd):
        srvs = dmd.Services
        srvRoots = ('IpServices',)
        self.addroots(srvs, srvRoots, "Services")

    def buildDevices(self, dmd):
        devices = dmd.Devices
        devroots = ('Servers', 'NetworkDevices',)
        self.addroots(devices, devroots[0:1], "Servers")
        self.addroots(devices, devroots[1:], "Devices")

    def buildServers(self, dmd):
        servers = dmd.Devices.Servers
        servRoots = ('Linux', 'Solaris', 'Windows')
        self.addroots(servers, servRoots, "Servers")
        cvRoots=('OOL', 'IO')
        self.addroots(dmd.Devices.Servers.Solaris, cvRoots, "Servers")

    def buildNetworkDevs(self, dmd):
        netdevs = dmd.Devices.NetworkDevices
        netRoots = ('Switch', 'CableModem')
        routerRoots = ('Router', 'RSM', 'Firewall')
        self.addroots(netdevs, netRoots, "Devices")
        self.addroots(netdevs, routerRoots, "Routers")
        self.addroots(netdevs, ('UBR',), "UbrRouters")

    def buildNetcool(self, dmd):
        if not hasattr(dmd, 'netcool'):
            from Products.NcoProduct.NcoProduct import NcoProduct
            nco = NcoProduct('netcool')
            nco.omniname = "NCOMS"
            nco.username = "ncoadmin"
            nco.password = "ncoadmin"
            nco.resultFields = [
                "System",
                "Node",
                "Summary",
                "LastOccurrence",
                "Tally",
                ]
            dmd._setObject(nco.id, nco)
            try:
                dmd._getOb(nco.id).manage_refreshConversions()
            except:
                print "Could not refresh Omnibus mappings, please do this by hand."

    def addroots(self, base, rlist, classType=None):
        for rname in rlist:
            ctype = classType or rname
            if not hasattr(base, rname):
                dr = classifications[ctype](rname)
                base._setObject(dr.id, dr)
                dr = base._getOb(dr.id)
                if dr.id in ('Devices','Systems','Networks'):
                    dr.createCatalog() 

    def buildSchema(self, dmd, file):
        if hasattr(dmd, 'ZenSchemaManager'):
            return None
        manage_addSchemaManager(dmd)
        sm = dmd._getOb('ZenSchemaManager')
        sm.loadSchemaFromFile(file)


    def buildClassifiers(self, dmd):
        if hasattr(dmd, 'ZenClassifier'):
            return
        manage_addClassifier(dmd)
        cl = dmd._getOb('ZenClassifier')
        snmpclassifiers = {
            'sysObjectIdClassifier' : '.1.3.6.1.2.1.1.2.0',
            'sysDescrClassifier' : '.1.3.6.1.2.1.1.1.0',
        }
        for sclname in snmpclassifiers.keys():
            manage_addSnmpClassifier(cl, sclname)
            snmpc = cl._getOb(sclname)
            snmpc.oid = snmpclassifiers[sclname]


    def buildCss(self, dmd):
        if hasattr(dmd, 'portal.css'):
            return None
        # add portal.css
        data = open('www/portal.css').read()
        portal = File('portal.css','portal.css',data)
        dmd._setObject(portal.id(), portal)


    def build(self, nco, schema, dmd):

        self.buildSchema(dmd, schema)
        self.buildClassifiers(dmd)
        self.buildRoots(dmd)
        self.buildMonitors(dmd)
        self.buildServices(dmd)
        self.buildProducts(dmd)
        self.buildDevices(dmd)
        self.buildServers(dmd)
        self.buildNetworkDevs(dmd)
        zd = ZDeviceLoader()
        dmd._setObject('DeviceLoader', zd)
        if nco: self.buildNetcool(dmd)
        #self.buildCss(dmd)
        get_transaction().note("initial load by DmdBuilder.py")
        get_transaction().commit()


#=================== begin main =================
from optparse import OptionParser
use = "%prog [-n] [-f schema]"
parser=OptionParser(usage=use, version="%prog " + __version__)
parser.add_option('-n', '--netcool',
                    dest='nco',
                    default=0,
                    action="store_true",
                    help="Add NcoProduct instance (needs sybase)")
parser.add_option('-f', '--filename',
                    dest="schema",
                    default="schema.data",
                    help="Location of the Dmd schema")
parser.add_option('-s', '--sitename',
                    dest="sitename",
                    default="zport",
                    help="name of portal object")
(options, args) = parser.parse_args()

schema = options.schema
nco = options.nco
#app = Zope.app()
site = getattr(app, options.sitename, None)
if not site:
    manage_addZentinelSite(app, options.sitename)
    site = app._getOb(options.sitename)

if not hasattr(aq_base(site), 'dmd'):
    dmd = DataRoot('dmd')
    site._setObject(dmd.id, dmd)

dmd = site._getOb('dmd')
dmdbuilder = DmdBuilder()
dmdbuilder.build(nco, schema, dmd)
sys.exit(0)
