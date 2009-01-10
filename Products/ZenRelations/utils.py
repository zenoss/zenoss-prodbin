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
from Exceptions import ZenImportError

def importClass(classpath, baseModule=None):
    """lookup a class by its path use baseModule path if passed"""
    import sys
    if baseModule: classpath = ".".join((baseModule, classpath))
    parts = classpath.split('.')
    try:
        mod = __import__(classpath)
        mod = sys.modules[classpath]
    except (ImportError, KeyError):
        try:
            base = ".".join(parts[:-1])
            mod = __import__(base)
            mod = sys.modules[base]
        except:
            raise ZenImportError("failed importing class %s" % classpath)
    return getattr(mod, parts[-1], mod)


def importClasses(basemodule=None, skipnames=()):
    """
    import all classes listed in baseModule in the variable productNames
    and return them in a list.  Assume that classes are defined in a file
    with the same name as the class.
    """
    classList = []
    mod = __import__(basemodule)
    for comp in basemodule.split(".")[1:]:
        mod = getattr(mod, comp)
    for prodname in mod.productNames:
        if prodname in skipnames: continue
        classdef = importClass(prodname, basemodule) 
        classList.append(classdef)
    return classList


class ZenRelationshipNameChooser(object):
    """
    Adapts a ZenRelation to find a unique id.
    """
    def __init__(self, context):
        self.context = context

    def chooseName(self, name):
        """
        Create an id.
        """
        dot = name.rfind('.')
        if dot >= 0:
            suffix = name[dot:]
            name = name[:dot]
        else:
            suffix = ''
        n = name + suffix
        i = 1
        inuse = self.context.objectIdsAll()
        while n in inuse:
            i += 1
            n = name + str(i) + suffix
        return str(n)


