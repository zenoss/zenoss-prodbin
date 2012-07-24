##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""RRDDataPointAlias

Create a simple level of indirection for normalization of data.  An alias is
a pair of a name and an rpn formula.  The formula should convert the datapoint
to the form represented by the name.

$Id:$"""
import Globals
from AccessControl import ClassSecurityInfo, Permissions

from Products.ZenUtils.ZenTales import talesEvalStr
from Products.ZenRelations.RelSchema import ToOne, ToManyCont
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.ZenPackable import ZenPackable
from Products.ZenUtils.deprecated import deprecated


ALIAS_DELIMITER = ','
EVAL_KEY = '__EVAL:'

@deprecated
def manage_addDataPointAlias( context, id, formula=None ):
    """
    Add a datapoint alias to the datapoint given
    """
    alias = RRDDataPointAlias( id )
    alias.formula = formula
    context.aliases._setObject( id, alias )
    return context.aliases._getOb( id )

class RRDDataPointAlias(ZenModelRM, ZenPackable):
    
    meta_type = 'RRDDataPointAlias'
    formula = None
    
    _properties = (
        {'id':'formula', 'type':'string', 'mode':'w'},
        )

    _relations = ZenPackable._relations + (
        ("datapoint", ToOne(ToManyCont,"Products.ZenModel.RRDDataPoint","aliases")),
        )


    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
    { 
        'immediate_view' : 'editRRDDataPoint',
        'actions'        :
        ( 
            { 'id'            : 'edit'
            , 'name'          : 'Data Point'
            , 'action'        : 'editRRDDataPoint'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )

    def evaluate(self, context):
        """
        Evaluate the formula with the given context so that the resulting
        rpn can be applied to the datapoint value.  There are two possible
        layers of evaluation: python and then TALES evaluation.  Both use the
        name 'here' to name the passed context.  See testRRDDataPointAlias for
        examples of usage.
        """
        if self.formula:
            formula = self.formula
            if formula.startswith( EVAL_KEY ):
                formula = formula[ len( EVAL_KEY ): ]
                formula = str( eval( formula, { 'here' : context } ) )    
            return talesEvalStr( formula, context ) 
        else:
            return None
