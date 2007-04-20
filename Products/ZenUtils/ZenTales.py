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

from Products.PageTemplates.Expressions import getEngine
from DateTime import DateTime

_compiled = {}
def talesEval(express, context):
    """Perform a TALES eval on the express using context.
    """
    compiled = talesCompile(express)    
    res = compiled(getEngine().getContext(
        {'here':context, 'nothing':None, 'now': DateTime() }))
    if isinstance(res, Exception):
        raise res
    return res

def talesCompile(express):
    compiled = _compiled.get(express, None)
    if not compiled:
        _compiled[express] = compiled = getEngine().compile(express)
    return compiled
