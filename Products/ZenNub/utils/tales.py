##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
from zope.tales.engine import Engine
from DateTime import DateTime

log = logging.getLogger("zen.nub.utils.tales")

class InvalidTalesException(Exception):
    pass


_compiled = {}

def talesEvalStr(expression, context, extra=None, skipfails=False):
    return talesEval('string:%s' % expression, context, extra, skipfails)


def talesEval(express, context, extra=None, skipfails=False):
    """Perform a TALES eval on the express using context.
    """
    try:
        compiled = talesCompile(express)
    except Exception as e:
        compiled = talesCompile("string:%s" % express)

    contextDict = { 'context':context,
                    'here':context,
                    'nothing':None,
                    'now': DateTime(),
                    }
    if isinstance(extra, dict):
        contextDict.update(extra)

    try:
        res = compiled(Engine.getContext(contextDict))
    except Exception, e:
        msg = "Error when processing tales expression %s on context %s : Exception Class %s Message: %s" % (express,
                                                                                                            context,
                                                                                                            type(e), e)
        if skipfails:
            res = express
            log.debug(msg)
        else:
            raise InvalidTalesException(msg)

    if isinstance(res, Exception):
        raise res
    return res

def talesCompile(express):
    compiled = _compiled.get(express, None)
    if not compiled:
        _compiled[express] = compiled = Engine.compile(express)
    return compiled
