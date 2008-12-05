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

__doc__="""utils

RRD utility functions
"""

from sets import Set
from Acquisition import aq_chain

from Exceptions import RRDObjectNotFound, TooManyArgs

def loadargs(obj, args):
    """
    Load data into a RRD Object

    @param obj: RRD object
    @type obj: RRD object
    @param args: arguments
    @type args: list of strings
    """
    import string
    arglen = len(args)
    if arglen > len(obj._properties):
        raise TooManyArgs( "Too many args" )
    i = 0
    for arg in args:
        if i > arglen: break
        arg = arg.strip()
        att = obj._properties[i]['id']
        try:
            if arg != '':
                if obj._properties[i]['type'] == 'lines':
                    value = map(string.strip, arg.split(','))
                    att = '_' + att
                elif obj._properties[i]['type'] == 'int':
                    value = int(arg)
                elif obj._properties[i]['type'] == 'long':
                    value = long(arg)
                elif obj._properties[i]['type'] == 'float':
                    value = float(arg)
                elif obj._properties[i]['type'] == 'boolean':
                    value = eval(arg)
                else:
                    value = arg
                if value is not None: setattr(obj,att,value)
        except:
            print "att = %s value = %s" % (att, arg)
            raise
        i += 1


def prefixid(idprefix, id):
    """
    See if prefix needs to be added to id

    @param idprefix: prefix
    @type idprefix: string
    @param id: identifier
    @type id: string
    @return: add the prefix with a '-' in between
    @rtype: string
    """
    if id.find(idprefix) != 0:
        id = idprefix + '-' + id    
    return id


def rootid(idprefix, id):
    """
    See if prefix needs to be removed from id

    @param idprefix: prefix
    @type idprefix: string
    @param id: identifier
    @type id: string
    @return: remove the prefix with a '-' in between or return None
    @rtype: string or None
    """
    if idprefix[-1] != '-': idprefix += '-'
    if id.find(idprefix) == 0:
        return id[len(idprefix):]


def walkupconfig(context, name):
    """
    Given a Zope context, try to find the rrdconfig object
    for the name.
    Raises RRDObjectNotFound if not found.

    @param context: Zope context
    @type context: Zope context object
    @param name: RRDView name
    @type name: string
    @return: rrdconfig object or None
    @rtype: rrdconfig object
    """
    if not name: return
    while 1:
        if hasattr(context, 'rrdconfig') and hasattr(context.rrdconfig, name):
            return getattr(context.rrdconfig, name)
        context = context.aq_parent
        if context.id == 'dmd':
            raise RRDObjectNotFound( "Object %s not found in context %s" % \
                                    (name, context.getPrimaryUrlPath()))
              

def templateNames(context):
    """
    Return template names in the given context

    @param context: Zope context
    @type context: Zope context object
    @return: names of the templates
    @rtype: set of strings
    """
    names = Set()
    for obj in aq_chain(context):
        rrdconfig = getattr(obj, 'rrdconfig', None)
        if rrdconfig:
            names = names.union(rrdconfig.objectIds(spec='RRDTargetType'))
    return names
             
        

def getRRDView(context, name):
    """
    Lookup an RRDView based on its name

    @param context: Zope context
    @type context: Zope context object
    @param name: RRDView name
    @type name: string
    @return: rrdconfig object or None
    @rtype: rrdconfig object
    """
    return walkupconfig(context, 'RRDView-'+name)


def getRRDTargetType(context, name):
    """
    Lookup an rrdtargettype based on its name

    @param context: Zope context
    @type context: Zope context object
    @param name: RRDView name
    @type name: string
    @return: rrdconfig object or None
    @rtype: rrdconfig object
    """
    return walkupconfig(context, 'RRDTargetType-'+name)


def getRRDDataSource(context, name):
    """
    Lookup an rrddatasource based on its name

    @param context: Zope context
    @type context: Zope context object
    @param name: RRDView name
    @type name: string
    @return: rrdconfig object or None
    @rtype: rrdconfig object
    """
    return walkupconfig(context, 'RRDDataSource-'+name)


def rpneval(value, rpn):
    """
    Totally bogus RPN evaluation only works with one-level stack

    @param value: something that can be used as a number
    @type value: string
    @param rpn: Reverse Polish Notatio (RPN) expression
    @type rpn: string
    @todo: make unbogus
    """
    if type(value) == type(''): return value
    operators = ('+','-','*','/')
    rpn = rpn.split(',')
    operator = ''
    for i in range(len(rpn)):
        symbol = rpn.pop()
        symbol = symbol.strip()
        if symbol in operators:
            operator = symbol
        else:
            expr = str(value) + operator + symbol
            value = eval(expr)
    return value
