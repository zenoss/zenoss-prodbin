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

__doc__="""GraphPoint

Defines attributes for how a data source will be graphed
and builds the nessesary rrd commands.
"""

from Globals import InitializeClass
from AccessControl import Permissions
from Products.ZenRelations.RelSchema import *
from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable

def manage_addGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = GraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class GraphPoint(ZenModelRM, ZenPackable):
    '''
    '''
    
    isThreshold = False

    DEFAULT_FORMAT = '%5.2lf%s'
    DEFAULT_LEGEND = '${graphPoint/id}'
    DEFAULT_MULTIGRAPH_LEGEND = '${here/name | here/id} ${graphPoint/id}'
    
    sequence = 0
    _properties = (
        {'id':'sequence', 'type':'long', 'mode':'w'},
        )

    _relations = ZenPackable._relations + (
        ("graphDef", ToOne(ToManyCont,"Products.ZenModel.GraphDefinition","graphPoints")),
        )
    
    factory_type_information = ( 
        { 
            'immediate_view' : 'editGraphPoint',
            'actions'        :
            ( 
                { 'id'            : 'edit'
                , 'name'          : 'Graph Point'
                , 'action'        : 'editGraphPoint'
                , 'permissions'   : ( Permissions.view, )
                },
            )
        },
    )

    colors = (
        '#00cc00', '#0000ff', '#00ffff', '#ff0000', 
        '#ffff00', '#cc0000', '#0000cc', '#0080c0',
        '#8080c0', '#ff0080', '#800080', '#0000a0',
        '#408080', '#808000', '#000000', '#00ff00',
        '#fb31fb', '#0080ff', '#ff8000', '#800000', 
        )


    ## Interface


    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        if self.graphDef.rrdTemplate():
            from RRDTemplate import crumbspath
            crumbs = super(GraphPoint, self).breadCrumbs(terminator)
            return crumbspath(self.graphDef(), crumbs, -3)
        return ZenModelRM.breadCrumbs(self, terminator)
        
        
    def manage_editProperties(self, REQUEST):
        '''
        '''
        if REQUEST.get('color', ''):
            REQUEST.color = '#%s' % REQUEST.color.lstrip('#')
        return self.zmanage_editProperties(REQUEST)


    def getDescription(self):
        ''' Return a description
        '''
        return self.id
        

    def getTalesContext(self, thing=None, **kw):
        '''
        Standard stuff to add to context for tales expressions
        '''
        context = {
            'graphDef': self.graphDef(),
            'graphPoint': self,
            }
        if thing:
            if thing.meta_type == 'Device':
                context['dev'] = thing
                context['devId'] = thing.id
            else:
                context['comp'] = thing
                context['compId'] = thing.id
                context['compName'] = thing.name()
                context['dev'] = thing.device()
                context['devId'] = thing.device().id
        for key, value in kw.items():
            context[key] = value
        return context


    def talesEval(self, str, context, **kw):
        '''
        return a tales evaluation of str
        '''
        from Products.ZenUtils.ZenTales import talesEvalStr
        extraContext = self.getTalesContext(thing=context, **kw)
        try:
            result = talesEvalStr(str, context, extraContext)
        except Exception:
            result = '(Tales expression error)'
        return result
            

    ## Graphing Support
    
    def getColor(self, index):
        index %= len(self.colors)
        color = self.color or self.colors[index]
        color = '#%s' % color.lstrip('#')
        if hasattr(self, 'stacked'): 
            if not self.stacked and index>0: color += "99"
            else: color += "ff"
        return color


    def getThresholdColor(self, index):
        index %= len(self.colors)
        color = self.color or self.colors[-1 * (index+1)]
        color = '#%s' % color.lstrip('#')
        return color


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                    multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        from Products.ZenUtils.Utils import unused
        unused(multiid, prefix, rrdDir)
        return cmds
        

    def getDsName(self, base, multiid=-1, prefix=''):
        name = self.addPrefix(prefix, base)
        if multiid > -1:
            name = '%s_%s' % (name, multiid)
        return name


    def addPrefix(self, prefix, base):
        ''' If not base then return ''
        elif prefix then return prefix_base
        else return base
        The result is rrd scrubbed
        '''
        s = base or ''
        if s and prefix:
            s = '_'.join((prefix, base))
        s = self.scrubForRRD(s)
        return s
        

    def scrubForRRD(self, value, namespace=None):
        ''' scrub value so it is a valid rrd variable name.  If namespace
        is provided then massage value as needed to avoid name conflicts
        with items in namespace.
        '''
        import string
        import itertools
        def Scrub(c):
            if c not in string.ascii_letters + string.digits + '_-':
                c = '_'
            return c            
        value = ''.join([Scrub(c) for c in value])
        if namespace:
            postfixIter = itertools.count(2)
            candidate = value
            while candidate in namespace:
                candidate = value + str(postfixIter.next())
            value = candidate
        return value


    def escapeForRRD(self, value):
        '''
        Escapes characters like colon ':' for use by RRDTool which would
        '''
        value = value.replace(":", "\:")
        return value


    def usesAttr(self, attr):
        """
        Return True if this graphpoint has the given attribute.
        This method exists for use in templates where the aq_base stuff
        is not so easily accessible.
        """
        return hasattr(self.aq_base, attr)


InitializeClass(GraphPoint)
