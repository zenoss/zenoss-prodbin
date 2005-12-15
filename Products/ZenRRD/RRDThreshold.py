#################################################################
#
#   Copyright (c) 2003 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""RRDThreshold

RRDThreshold defines a list of datasource names and rrdview names
as well as a mechanism that will look them using acquisition.

$Id: RRDThreshold.py,v 1.11 2003/11/13 22:52:42 edahl Exp $"""

__version__ = "$Revision: 1.11 $"[11:-2]

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Globals import DTMLFile
from OFS.PropertyManager import PropertyManager

from RRDToolItem import RRDToolItem

import utils

def manage_addRRDThreshold(context, id, REQUEST = None):
    """make a RRDThreshold"""
    tt = RRDThreshold(id)
    context._setObject(tt.id, tt)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')

addRRDThreshold = DTMLFile('dtml/addRRDThreshold',globals())

class RRDThreshold(RRDToolItem, PropertyManager):
    
    meta_type = 'RRDThreshold'
    
    security = ClassSecurityInfo()
 
    manage_options = PropertyManager.manage_options + \
                     RRDToolItem.manage_options
    _properties = (
                 {'id':'dsnames', 'type':'lines', 'mode':'w'},
                 {'id':'minval', 'type':'long', 'mode':'w'},
                 {'id':'maxval', 'type':'long', 'mode':'w'},
                 {'id':'minvalfunc', 'type':'string', 'mode':'w'},
                 {'id':'maxvalfunc', 'type':'string', 'mode':'w'},
                )

    def __init__(self, id, dsnames=[], maxval=0L, minval=0L,
                maxvalfunc='', minvalfunc=''):

        self.id = utils.prefixid(self.meta_type, id)
        self._dsnames = []
        map(self.addDs, dsnames)
        self.maxval = maxval
        self.minval = minval
        self.maxvalfunc = maxvalfunc
        self.minvalfunc = minvalfunc
  
  
    def textload(self, args):
        """called by RRDLoader to populate TargetType datasources and views
        args should have camma separated list of dsnames and viewnames"""
        utils.loadargs(self, args) 


    def __getattr__(self, name):
        if name == 'dsnames':
            return self._dsnames
        else:
            raise AttributeError, name


    def _setPropValue(self, id, value):
        """override from PerpertyManager to handle checks and ip creation"""
        self._wrapperCheck(value)
        if id == 'dsnames':
            self.setDsNames(value)
        else:    
            setattr(self,id,value)


    def setDsNames(self, dsnames):
        """set the entire list of datasource names that this threshold checks"""
        self._dsnames = []
        map(self.addDs, dsnames)


    def addDs(self, dsname):
        dsname = dsname.strip()
        if dsname:
            self._dsnames.append(dsname)
            self._p_changed = 1 


    def getMaxval(self, context):
        """get the max value of this threshold"""
        return self.getValue(self.maxval, self.maxvalfunc, context)


    def getMinval(self, context):
        """get the min value of this threshold"""
        value = self.getValue(self.minval, self.minvalfunc, context)
        if not value: value = 'n'
        return value
       
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


    def getValue(self, value, valuefunc, context):
        """do the actual work of figuring out thresh values
        if a fixed number is set in value return it else
        eval the function in valuefunc context is the object
        against which the threshold will be evaluated in cricket"""
        if valuefunc:
            value = eval(valuefunc)
        return value 


    def getCricketThresholds(self, context):
        """return the cricket threshold string that this threshold defines"""
        threshs = []
        for ds in self._dsnames:
            minval = str(self.getMinval(context))
            maxval = self.getMaxval(context)
            if maxval > 0:
                maxval = str(maxval)
                thresh = ':'.join((ds,'value',minval,maxval,'SNMP'))
                if thresh.strip(): threshs.append(thresh)
        return ','.join(threshs)


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
