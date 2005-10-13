#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""Utils

General Utility function module

$Id: Utils.py,v 1.15 2004/04/04 02:22:38 edahl Exp $"""

__version__ = "$Revision: 1.15 $"[11:-2]

import types
import struct

from Acquisition import aq_base

from Products.ZenUtils.Exceptions import ZenPathError

def travAndColl(obj, toonerel, collect, collectname):
    """walk a series of to one rels collecting collectname into collect"""
    #from Acquisition import aq_base
    value = getattr(aq_base(obj), collectname, None)
    if value:
        collect.append(value)
    rel = getattr(aq_base(obj), toonerel, None)
    if callable(rel):
        nobj = rel()
        if nobj:
            return travAndColl(nobj, toonerel, collect, collectname)
    return collect


def getObjByPath(base, path):
    """walk our path to see if it still is valid
    path can be a string in the form /dmd/Devices/Servers/Linux/b.zetinel.net
    or it can be sequence of strings that starts with the dmd object ie:
    ('dmd', 'Devices', 'Servers', 'Linux', 'b.zentinel.net')
    maybe this can be replaced by unrestrictedtraverse?"""
    #from Acquisition import aq_base
    if path:
        if type(path) == types.StringType or type(path) == types.UnicodeType:
            if path[0] == "/": path=path[1:]
            path = path.split('/')
        if hasattr(aq_base(base), path[0]):
            nobj = getattr(base, path[0])
            # if we have to skip over a relationship to find the children
            #if hasattr(nobj, "subObjectsName"):
            #    subObjectsName = getattr(nobj, "subObjectsName") 
            #    if len(path) > 1 and path[1] != subObjectsName:
            #        nobj = getattr(nobj, subObjectsNameone)
            return getObjByPath(nobj, path[1:])
        #Look for related object with full id in ToManyRelation
        elif hasattr(aq_base(base), "/"+"/".join(path)):
            base = getattr(base, "/"+"/".join(path))
        else:
            base = None
    return base


def checkClass(myclass, className):
    """perform issubclass using class name as string"""
    if myclass.__name__ == className:
        return 1
    for mycl in myclass.__bases__:
        if checkClass(mycl, className):
            return 1


def parseconfig(options):
    """parse a config file which has key value pairs delimited by white space"""
    lines = open(options.configfile).readlines()
    for line in lines:
        if line[1] == '#': continue
        key, value = line.split()
        key = key.lower()
        setattr(options, key, value)


def lookupClass(productName, classname=None):
        """look in sys.modules for our class"""
        import sys
        if sys.modules.has_key(productName):
            mod = sys.modules[productName]
        elif sys.modules.has_key("Products."+productName):
            mod = sys.modules["Products."+productName]
        else:
            return None
        if not classname:
            classname = productName.split('.')[-1]
        return getattr(mod,classname)


def cleanstring(value):
    """take the trailing \x00 off the end of a string"""
    if type(value) == types.StringType and value[-1] == struct.pack('x'):
        value = value[:-1]
    return value


def getSubObjects(base, filter=None, decend=None, retobjs=[]):
    """do a depth first search looking for objects that the function filter
    returns as true. If decend is passed it will check to see if we
    should keep going down or not"""
    if not retobjs: retobjs = []
    for obj in base.objectValues():
        if not filter or filter(obj):
            retobjs.append(obj)
        if not decend or decend(obj):
            retobjs = getSubObjects(obj, filter, decend, retobjs)
    return retobjs


def getSubObjectsMemo(base, filter=None, decend=None, memo={}):
    """do a depth first search looking for objects that the function filter
    returns as true. If decend is passed it will check to see if we
    should keep going down or not"""
    from Products.ZenRelations.RelationshipManager \
        import RelationshipManager
    if base.meta_type == "To One Relationship":
        objs = [base.obj]
    else:
        objs = base.objectValues()
    for obj in objs:
        if (isinstance(obj, RelationshipManager) and 
            not obj.getPrimaryDmdId().startswith(base.getPrimaryDmdId())): 
            continue
        if not filter or filter(obj):
            yield obj
        if not decend or decend(obj):
            for x in getSubObjectsMemo(obj, filter, decend, memo):
                yield x


def getAllConfmonObjects(base):
    """get all ZenModelRM objects in database"""
    from Products.ZenModel.Instance import Instance
    from Products.ZenModel.ZenModelRM import ZenModelRM
    from Products.ZenRelations.ToManyRelationship \
        import ToManyRelationship
    from Products.ZenRelations.ToOneRelationship \
        import ToOneRelationship
    def decend(obj):
        return (
                isinstance(obj, ZenModelRM) or 
                isinstance(obj, ToManyRelationship) or
                isinstance(obj, ToOneRelationship))
    def filter(obj):
        return isinstance(obj, Instance) and obj.id != "dmd"
    return getSubObjectsMemo(base, filter=filter, decend=decend)

def zenpathsplit(pathstring):
    """split a zen path and clean up any blanks or bogus spaces in it"""
    path = pathstring.split("/")
    path = filter(lambda x: x, path)
    path = map(lambda x: x.strip(), path)
    return path

def zenpathjoin(pathar):
    """build a zenpath in its string form"""
    return "/" + "/".join(pathar)

def OLDgetHierarchyObj(root, name, factory, lastfactory=None, 
                    relpath=None, lastrelpath=None, log=None):
    """build and return the path to an object 
    based on a hierarchical name (ex /Mail/Mta) relative
    to the root passed in.  If lastfactory is passed the leaf object
    will be created with it instead of factory. 
    relpath is the relationship within which we will recurse as
    objects are created.  Having the relationship in the path passed
    is optional."""
    path = zenpathsplit(name)
    for id in path:
        if id == relpath: continue
        if getattr(aq_base(root), id, False):
            nextroot = getattr(root, id)
        else:
            if id == path[-1]:
                if lastrelpath: relpath = lastrelpath
                if lastfactory: factory = lastfactory 
            if relpath and getattr(aq_base(root), relpath, False):
                relobj = getattr(root, relpath)
                if not getattr(aq_base(relobj), id, False):
                    if log: log.debug(
                        "creating object with id %s in relation %s" % 
                        (id, relobj.getId()))
                    factory(relobj, id)
                nextroot = relobj._getOb(id)
            else:
                if log: log.debug("creating object with id %s"%id)
                factory(root, id)
                nextroot = root._getOb(id)
        root = nextroot
    return root


def createHierarchyObj(root, name, factory, relpath="", log=None):
    """
    Create a hierarchy object from its path we use relpath to skip down
    any missing relations in the path and factory is the constructor for 
    this object.
    """
    rootName = root.id
    for id in zenpathsplit(name):
        if id == rootName: continue
        if id == relpath or getattr(aq_base(root), relpath, False):
            root = getattr(root, relpath)
        if not getattr(aq_base(root), id, False):
            if id == relpath: 
                raise AttributeError("relpath %s not found" % relpath)
            if log: log.debug("Creating object with id %s in object %s" % 
                            (id, root.getId()))
            newobj = factory(id)
            root._setObject(id, newobj)
        root = getattr(root, id)
    return root


def getHierarchyObj(root, name, relpath=None):
    """Return an object using its path relations are optional in the path."""
    for id in zenpathsplit(name):
        if id == relpath or getattr(aq_base(root), relpath, False):
            root = getattr(root, relpath)
        if not getattr(root, id, False):
            raise ZenPathError("Path %s id %s not found on object %s" %
                                (name, id, root.getPrimaryId()))
        root = getattr(root, id, None)
    return root
    


def basicAuthUrl(username, password, url):
    """add the username and password to a url in the form
    http://username:password@host/path"""
    urlar = url.split('/')
    if not username or not password or urlar[2].find('@') > -1: 
        return url 
    urlar[2] = "%s:%s@%s" % (username, password, urlar[2])
    return "/".join(urlar)
