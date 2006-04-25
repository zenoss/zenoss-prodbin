#################################################################
#
#   Copyright (c) 2003 Zenoss, Inc. All rights reserved.
#
#################################################################

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions

from ZenModelRM import ZenModelRM

from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.ZenTales import talesEval


def manage_addRRDThreshold(context, id, REQUEST = None):
    """make a RRDThreshold"""
    tt = RRDThreshold(id)
    context._setObject(tt.id, tt)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')

addRRDThreshold = DTMLFile('dtml/addRRDThreshold',globals())

class RRDThreshold(ZenModelRM):
    
    meta_type = 'RRDThreshold'
    
    security = ClassSecurityInfo()
 
    dsnames = []
    minval = ""
    maxval = ""
    severity = 3
    escalateCount = 0

    _properties = (
                 {'id':'dsnames', 'type':'string', 'mode':'w'},
                 {'id':'minval', 'type':'string', 'mode':'w'},
                 {'id':'maxval', 'type':'string', 'mode':'w'},
                 {'id':'severity', 'type':'int', 'mode':'w'},
                 {'id':'escalateCount', 'type':'int', 'mode':'w'},
                )

    _relations =  (
        ("rrdTemplate", ToOne(ToManyCont,"RRDTemplate", "thresholds")),
        )


    factory_type_information = ( 
    { 
        'immediate_view' : 'editRRDThreshold',
        'actions'        :
        ( 
            { 'id'            : 'edit'
            , 'name'          : 'RRD Threshold'
            , 'action'        : 'editRRDThreshold'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )
    
    def getConfig(self, context):
        """Return the config used by the collector to process simple min/max
        thresholds. (id, minval, maxval, severity, escalateCount)
        """
        minval = None
        maxval = None
        if self.minval:
            minval = talesEval("python:"+self.minval, context)
        if self.maxval:
            maxval = talesEval("python:"+self.maxval, context)
        return (self.id,minval,maxval,self.severity,self.escalateCount)
   

    def getGraphMinval(self, context):
        """when graphing use this so that rpn conversions are accounted for"""
        ds = None
        try:
            ds = utils.getRRDDataSource(context, self._dsnames[0])
        except utils.RRDObjectNotFound: pass    
        if ds and ds.rpn:
            return utils.rpneval(self.getMinval(context), ds.rpn)
        else:
            return self.getMinval(context)


    def getGraphMaxval(self, context):
        """when graphing use this so that rpn conversions are accounted for"""
        ds = None
        try:
            ds = utils.getRRDDataSource(context, self._dsnames[0])
        except utils.RRDObjectNotFound: pass    
        if ds and ds.rpn:
            return utils.rpneval(self.getMaxval(context), ds.rpn)
        else:
            return self.getMaxval(context)


    def getMinLabel(self, context):
        """build a label for a min threshold"""
        rootid = utils.rootid(self.meta_type, self.id)
        return "%s < %s" % (rootid, self.setPower(self.getGraphMinval(context)))


    def getMaxLabel(self, context):
        """build a label for a max threshold"""
        rootid = utils.rootid(self.meta_type, self.id)
        return "%s > %s" % (rootid, self.setPower(self.getGraphMaxval(context)))


    def setPower(self, number):
        powers = ("k", "M", "G")
        if number < 1000: return number
        for power in powers:
            number = number / 1000
            if number < 1000:  
                return "%0.3f%s" % (number, power)
        return "%.3f%s" % (number, powers[-1])


InitializeClass(RRDThreshold)
