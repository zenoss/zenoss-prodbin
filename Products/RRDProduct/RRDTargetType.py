#################################################################
#
#   Copyright (c) 2003 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""RRDTargetType

RRDTargetType defines a list of datasource names and rrdview names
as well as a mechanism that will look them using acquisition.

$Id: RRDTargetType.py,v 1.11 2003/11/13 22:52:42 edahl Exp $"""

__version__ = "$Revision: 1.11 $"[11:-2]

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Globals import DTMLFile
from OFS.PropertyManager import PropertyManager

from RRDToolItem import RRDToolItem
from RRDDataSource import RRDDataSource
from RRDView import RRDView
from RRDThreshold import RRDThreshold

import utils

def manage_addRRDTargetType(context, id, REQUEST = None):
    """make a RRDTargetType"""
    tt = RRDTargetType(id)
    context._setObject(tt.id, tt)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

addRRDTargetType = DTMLFile('dtml/addRRDTargetType',globals())


def lookupTargetType(context, name):
    return utils.walkupconfig(context, 
        utils.prefixid(RRDTargetType.meta_type, name))
    

class RRDTargetTypeError(utils.RRDException): pass

class RRDTargetType(RRDToolItem, PropertyManager):

    meta_type = 'RRDTargetType'

    security = ClassSecurityInfo()
   
    manage_options = PropertyManager.manage_options + \
                     RRDToolItem.manage_options
    _properties = (
                 {'id':'dsnames', 'type':'lines', 'mode':'w'},
                 {'id':'viewnames', 'type':'lines', 'mode':'w'},
                 {'id':'thresholds', 'type':'lines', 'mode':'w'},
                )

    def __init__(self, id):
        self.id = utils.prefixid(self.meta_type, id)
        self._dsnames = []
        self._viewnames = []
        self._thresholds = []
  
  
    def textload(self, args):
        """called by RRDLoader to populate TargetType datasources and views
        args should have camma separated list of dsnames and viewnames"""
        utils.loadargs(self, args) 
    

    def __getattr__(self, name):
        if name == 'dsnames':
            return self._dsnames
        if name == 'viewnames':
            return self._viewnames
        if name == 'thresholds':
            return self._thresholds
        else:
            raise AttributeError, name


    def _setPropValue(self, id, value):
        """override from PerpertyManager to handle checks and ip creation"""
        self._wrapperCheck(value)
        if id == 'dsnames':
            self.setDsNames(value)
        elif id == 'viewnames':
            self.setViewNames(value)
        elif id == 'thresholds':
            self.setThresholds(value)
        else:    
            setattr(self,id,value)


    def addToList(self, list, value):
        value = value.strip()
        if value:
            list.append(value)
            self._p_changed = 1 


    def setDsNames(self, dsnames):
        """set the entire list of datasource names"""
        self._dsnames = []
        map(self.addDs, dsnames)


    def addDs(self, dsname):
        self.addToList(self._dsnames, dsname) 


    def getDs(self, context, name):
        """get datasource by name using acquisition"""
        index = -1
        try:
            index = self._dsnames.index(name)
        except ValueError:
            raise RRDTargetTypeError, \
                "Datasource %s is not part of RRDTargetType %s" % \
                                                    (name, self.id)
        name = utils.prefixid(RRDDataSource.meta_type, name)
        try:
            ds = utils.walkupconfig(context, name)
        except utils.RRDObjectNotFound:
            #if we can find one make using defaults and wrap it
            ds = RRDDataSource(name)
            ds.__of__(self)
            
        ds.setIndex(index)
        return ds


    def setViewNames(self, viewnames):
        self._viewnames = []
        map(self.addViewName, viewnames)


    def addViewName(self, viewname):
        self.addToList(self._viewnames, viewname)

    
    def getDefaultViewName(self):
        """return the first view in the view list as the default"""
        if len(self._viewnames):
            return self._viewnames[0]
   

    def getViewNames(self):
        return self._viewnames


    def getViews(self, context):
        views = []
        for viewname in self._viewnames:
            views.append(self.getView(context, viewname))
        return views


    def getView(self, context, name):
        return utils.getRRDView(context, name)


    def getDefaultView(self, context):
        name = self.getDefaultViewName()
        return self.getView(context, name)


    def setThresholds(self, thresholds):
        self._thresholds = []
        map(self.addThreshold, thresholds)


    def addThreshold(self, threshold):
        self.addToList(self._thresholds, threshold)


    def getThresholds(self, context):
        """return a list of actual threshold objects for this target type"""
        threshs = []
        for threshname in self._thresholds:
            threshs.append(self.getThreshold(context, threshname))
        return threshs
            
        
    def getThreshold(self, context, name):
        """return an actual threshold object for this target type"""
        try:
            thresh = utils.walkupconfig(context, name)
        except utils.RRDObjectNotFound:
            name = utils.prefixid(RRDThreshold.meta_type, name)
            thresh = utils.walkupconfig(context, name)
        return thresh


    def getCricketThresholds(self, context):
        threshs = self.getThresholds(context)
        cthreshs = []
        for thresh in threshs:
            cthreshs.append(thresh.getCricketThresholds(context))
        if cthreshs:
            cthreshs = filter(lambda x: x, cthreshs)
            return ','.join(cthreshs)


InitializeClass(RRDTargetType)
