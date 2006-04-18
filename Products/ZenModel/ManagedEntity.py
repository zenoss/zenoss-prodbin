#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""ManagedEntity

$Id: DeviceComponent.py,v 1.1 2004/04/06 21:05:03 edahl Exp $"""

import logging
log = logging.getLogger("zen.DeviceComponent")

from ZenModelRM import ZenModelRM
from DeviceResultInt import DeviceResultInt
from RRDView import RRDView
from EventView import EventView

from Acquisition import aq_base

from Products.ZenRelations.RelSchema import *
from Products.ZenRRD.utils import RRDObjectNotFound 
from Products.ZenRRD.RRDTargetType import lookupTargetType

class ManagedEntity(ZenModelRM, DeviceResultInt, EventView, RRDView):
    """
    ManagedEntity is an entity in the system that is managed by it.
    Its basic property is that it can be classified by the ITClass Tree.
    Also has EventView and RRDView available.
    """

    # list of performance multigraphs (see PerformanceView.py)
    # FIXME this needs to go to some new setup and doesn't work now
    #_mgraphs = []

    # primary snmpindex for this managed entity
    snmpindex = 0

    _properties = (
                 {'id':'snmpindex', 'type':'int', 'mode':'w'},
                )    

    _relations = (
        ("dependenices", ToMany(ToMany, "ManagedEntity", "dependants")),
        ("dependants", ToMany(ToMany, "ManagedEntity", "dependenices")),
    )
    
    def device(self):
        """Overridden in lower classes if a device relationship exists.
        """
        return None


    def snmpIgnore(self):
        """Should this component be monitored for performance using snmp.
        """
        return False


    def getSnmpOidTargets(self):
        """Return a list of (oid, path, type) that define monitorable 
        """
        oids = []
        if self.snmpIgnore(): return oids 
        basepath = self.getPrimaryDmdId()
        try:
            ttype = lookupTargetType(self, self.getRRDTargetName())
            for dsname in ttype.dsnames:
                ds = ttype.getDs(self, dsname)
                oid = ds.oid
                snmpindex = getattr(self, "ifindex", self.snmpindex) #FIXME
                if ds.isrow: oid = "%s.%d" % (oid, snmpindex)
                oids.append((oid, "/".join((basepath, dsname)), ds.rrdtype))
        except RRDObjectNotFound, e:
            log.warn(e)
        return oids
