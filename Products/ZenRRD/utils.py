#################################################################
#
#   Copyright (c) 2003 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""utils

utility functions for RRDProduct

$Id: utils.py,v 1.9 2003/05/12 16:13:28 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]


from Products.ZenUtils.Exceptions import ZentinelException

class RRDException(ZentinelException): pass

class RRDObjectNotFound(RRDException): pass

class TooManyArgs(RRDException): pass

def loadargs(obj, args):
    """Load data into a RRD Object"""
    import string
    arglen = len(args)
    if arglen > len(obj._properties): raise TooManyArgs, "Too many args"
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
                else:
                    value = arg
                if value: setattr(obj,att,value)
        except:
            print "att = %s value = %s" % (att, arg)
            raise
        i += 1


def prefixid(idprefix, id):
    """see if prefix needs to be added to id"""
    if id.find(idprefix) != 0:
        id = idprefix + '-' + id    
    return id


def rootid(idprefix, id):
    if idprefix[-1] != '-': idprefix += '-'
    if id.find(idprefix) == 0:
        return id[len(idprefix):]


def walkupconfig(context, name):
    if not name: return
    while 1:
        if hasattr(context, 'rrdconfig') and hasattr(context.rrdconfig, name):
            return getattr(context.rrdconfig, name)
        context = context.aq_parent
        if context.id == 'dmd':
            raise RRDObjectNotFound,"Object %s not found in context %s" % \
                                    (name, context.getPrimaryUrlPath())
               

def getRRDView(context, name):
    """lookup an rrdview based on its name"""
    return walkupconfig(context, 'RRDView-'+name)


def getRRDTargetType(context, name):
    """lookup an rrdtargettype based on its name"""
    return walkupconfig(context, 'RRDTargetType-'+name)


def getRRDDataSource(context, name):
    """lookup an rrddatasource based on its name"""
    return walkupconfig(context, 'RRDDataSource-'+name)


def rpneval(value, rpn):
    """totally bogus rpn valuation only works with one level stack"""
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
