#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

from Products.PageTemplates.Expressions import getEngine

_compiled = {}
def talesEval(express, context):
    """Perform a TALES eval on the express using context.
    """
    compiled = _compiled.get(express, None)
    if not compiled:
        _compiled[express] = compiled = getEngine().compile(express)
    res = compiled(getEngine().getContext({'here':context, 'nothing':None}))
    if isinstance(res, Exception):
        raise res
    return res

