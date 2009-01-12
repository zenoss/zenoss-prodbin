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

__doc__="""Utils

General utility functions module

"""

import sys
import select
import popen2
import fcntl
import time
import os
import types
import logging
import re
import socket
import warnings
import math
from decimal import Decimal
from sets import Set
log = logging.getLogger("zen.Utils")

from popen2 import Popen4

from Acquisition import aq_base
from zExceptions import NotFound
from AccessControl import getSecurityManager
from AccessControl import Unauthorized
from AccessControl.ZopeGuards import guarded_getattr
from Acquisition import aq_inner, aq_parent

from Products.ZenUtils.Exceptions import ZenPathError, ZentinelException

class HtmlFormatter(logging.Formatter):
    """
    Formatter for the logging class
    """

    def __init__(self):
        logging.Formatter.__init__(self, 
        """<tr class="loggingRow">
        <td>%(asctime)s</td><td>%(levelname)s</td>
        <td>%(name)s</td><td>%(message)s</td>
        </tr>
        """,
        "%Y-%m-%d %H:%M:%S")

    def formatException(self, exc_info):
        """
        Format a Python exception

        @param exc_info: Python exception containing a description of what went wrong
        @type exc_info: Python exception class
        @return: formatted exception
        @rtype: string
        """
        exc = logging.Formatter.formatException(self,exc_info)
        return """<tr class="tablevalues"><td colspan="4">%s</td></tr>""" % exc


def setWebLoggingStream(stream):
    """
    Setup logging to log to a browser using a request object.

    @param stream: IO stream
    @type stream: stream class
    @return: logging handler
    @rtype: logging handler
    """
    handler = logging.StreamHandler(stream)
    handler.setFormatter(HtmlFormatter())
    rlog = logging.getLogger()
    rlog.addHandler(handler)
    rlog.setLevel(logging.ERROR)
    zlog = logging.getLogger("zen")
    zlog.setLevel(logging.INFO)
    return handler


def clearWebLoggingStream(handler):
    """
    Clear our web logger.

    @param handler: logging handler
    @type handler: logging handler
    """
    rlog = logging.getLogger()
    rlog.removeHandler(handler)


def convToUnits(number=0, divby=1024.0, unitstr="B"):
    """
    Convert a number to its human-readable form. ie: 4GB, 4MB, etc.

        >>> convToUnits() # Don't do this!
        '0.0B'
        >>> convToUnits(None) # Don't do this!
        ''
        >>> convToUnits(123456789)
        '117.7MB'
        >>> convToUnits(123456789, 1000, "Hz")
        '123.5MHz'

    @param number: base number
    @type number: number
    @param divby: divisor to use to convert to appropriate prefix
    @type divby: number
    @param unitstr: base unit of the number
    @type unitstr: string
    @return: number with appropriate units
    @rtype: string
    """
    units = map(lambda x:x + unitstr, ('','K','M','G','T','P'))
    try:
        numb = float(number)
    except:
        return ''

    sign = 1
    if numb < 0:
        numb = abs(numb)
        sign = -1
    for unit in units:
        if numb < divby: break
        numb /= divby
    return "%.1f%s" % (numb * sign, unit)
        

def travAndColl(obj, toonerel, collect, collectname):
    """
    Walk a series of to one rels collecting collectname into collect

    @param obj: object inside of Zope
    @type obj: object
    @param toonerel: a to-one relationship object
    @type toonerel: toonerel object
    @param collect: object list
    @type collect: list
    @param collectname: name inside of the to-one relation object
    @type collectname: string
    @return: list of objects
    @rtype: list
    """
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


def getObjByPath(base, path, restricted=0):
    """
    Get a Zope object by its path (e.g. '/Devices/Server/Linux').
    Mostly a stripdown of unrestrictedTraverse method from Zope 2.8.8.

    @param base: base part of a path
    @type base: string
    @param path: path to an object inside of the DMD
    @type path: string
    @param restricted: flag indicated whether to use securityManager
    @type restricted: integer
    @return: object pointed to by the path
    @rtype: object
    """
    if not path:
        return base

    _getattr = getattr
    _none = None
    marker = object()

    if isinstance(path, str):
        # Unicode paths are not allowed
        path = path.split('/')
    else: 
        path = list(path)

    REQUEST = {'TraversalRequestNameStack': path}
    path.reverse()
    path_pop=path.pop

    if len(path) > 1 and not path[0]:
        # Remove trailing slash
        path.pop(0)

    if restricted: 
        securityManager = getSecurityManager()
    else: 
        securityManager = _none

    if not path[-1]:
        # If the path starts with an empty string, go to the root first.
        path_pop()
        base = base.getPhysicalRoot()
        if (restricted 
            and not securityManager.validate(None, None, None, base)):
            raise Unauthorized( base )

    obj = base
    while path:
        name = path_pop()

        if name[0] == '_':
            # Never allowed in a URL.
            raise NotFound( name )

        if name == '..':
            next = aq_parent(obj)
            if next is not _none:
                if restricted and not securityManager.validate(
                    obj, obj,name, next):
                    raise Unauthorized( name )
                obj = next
                continue

        bobo_traverse = _getattr(obj, '__bobo_traverse__', _none)
        if bobo_traverse is not _none:
            next = bobo_traverse(REQUEST, name)
            if restricted:
                if aq_base(next) is not next:
                    # The object is wrapped, so the acquisition
                    # context is the container.
                    container = aq_parent(aq_inner(next))
                elif _getattr(next, 'im_self', _none) is not _none:
                    # Bound method, the bound instance
                    # is the container
                    container = next.im_self
                elif _getattr(aq_base(obj), name, marker) == next:
                    # Unwrapped direct attribute of the object so
                    # object is the container
                    container = obj
                else:
                    # Can't determine container
                    container = _none
                try:
                    validated = securityManager.validate(
                                           obj, container, name, next)
                except Unauthorized:
                    # If next is a simple unwrapped property, it's
                    # parentage is indeterminate, but it may have been
                    # acquired safely.  In this case validate will
                    # raise an error, and we can explicitly check that
                    # our value was acquired safely.
                    validated = 0
                    if container is _none and \
                           guarded_getattr(obj, name, marker) is next:
                        validated = 1
                if not validated:
                    raise Unauthorized( name )
        else:
            if restricted:
                next = guarded_getattr(obj, name, marker)
            else:
                next = _getattr(obj, name, marker)
                ## Below this is a change from the standard traverse from zope
                ## it allows a path to use acquisition which is not what
                ## we want.  Our version will fail if one element of the
                ## path doesn't exist. -EAD
                #if hasattr(aq_base(obj), name):
                #    next = _getattr(obj, name, marker)
                #else:
                #    raise NotFound, name
            if next is marker:
                try:
                    next=obj[name]
                except AttributeError:
                    # Raise NotFound for easier debugging
                    # instead of AttributeError: __getitem__
                    raise NotFound( name )
                if restricted and not securityManager.validate(
                    obj, obj, _none, next):
                    raise Unauthorized( name )
        obj = next
    return obj



def checkClass(myclass, className):
    """
    Perform issubclass using class name as string

    @param myclass: generic object
    @type myclass: object
    @param className: name of a class
    @type className: string
    @return: the value 1 if found or None
    @rtype: integer or None
    """
    if myclass.__name__ == className:
        return 1
    for mycl in myclass.__bases__:
        if checkClass(mycl, className):
            return 1


def lookupClass(productName, classname=None):
    """
    look in sys.modules for our class

    @param productName: object in Products
    @type productName: string
    @param classname: class name
    @type classname: string
    @return: object at the classname in Products
    @rtype: object or None
    """
    if sys.modules.has_key(productName):
       mod = sys.modules[productName]

    elif sys.modules.has_key("Products."+productName):
       mod = sys.modules["Products."+productName]

    else:
       return None

    if not classname:
       classname = productName.split('.')[-1]

    return getattr(mod,classname)


def importClass(modulePath, classname=""):
    """
    Import a class from the module given.

    @param modulePath: path to module in sys.modules
    @type modulePath: string
    @param classname: name of a class
    @type classname: string
    @return: the class in the module
    @rtype: class
    """
    try:
        if not classname: classname = modulePath.split(".")[-1]
        try:
            __import__(modulePath, globals(), locals(), classname)
            mod = sys.modules[modulePath]
        except (ValueError, ImportError, KeyError), ex:
            raise ex
        
        return getattr(mod, classname)
    except AttributeError:
        raise ImportError("Failed while importing class %s from module %s" % (
                            classname, modulePath))


def cleanstring(value):
    """
    Take the trailing \x00 off the end of a string

    @param unitstr: sample string
    @type unitstr: string
    @return: cleaned string
    @rtype: string
    """
    if type(value) in types.StringTypes:
        value = value.split('\0')[0]
    return value


def getSubObjects(base, filter=None, descend=None, retobjs=None):
    """
    Do a depth-first search looking for objects that the function filter
    returns as True. If descend is passed it will check to see if we
    should keep going down or not

    @param base: base object to start search
    @type base: object
    @param filter: filter to apply to each object to determine if it gets added to the returned list
    @type filter: function or None
    @param descend: function to apply to each object to determine whether or not to continue searching
    @type descend: function or None
    @param retobjs: list of objects found
    @type retobjs: list
    @return: list of objects found
    @rtype: list
    """
    if not retobjs: retobjs = []
    for obj in base.objectValues():
        if not filter or filter(obj):
            retobjs.append(obj)
        if not descend or descend(obj):
            retobjs = getSubObjects(obj, filter, descend, retobjs)
    return retobjs


def getSubObjectsMemo(base, filter=None, descend=None, memo={}):
    """
    Do a depth-first search looking for objects that the function filter
    returns as True. If descend is passed it will check to see if we
    should keep going down or not.

    This is a Python iterable.

    @param base: base object to start search
    @type base: object
    @param filter: filter to apply to each object to determine if it gets added to the returned list
    @type filter: function or None
    @param descend: function to apply to each object to determine whether or not to continue searching
    @type descend: function or None
    @param memo: dictionary of objects found (unused)
    @type memo: dictionary
    @return: list of objects found
    @rtype: list
    """
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
        if not descend or descend(obj):
            for x in getSubObjectsMemo(obj, filter, descend, memo):
                yield x


def getAllConfmonObjects(base):
    """
    Get all ZenModelRM objects in database

    @param base: base object to start searching
    @type base: object
    @return: list of objects
    @rtype: list
    """
    from Products.ZenModel.ZenModelRM import ZenModelRM
    from Products.ZenModel.ZenModelBase import ZenModelBase
    from Products.ZenRelations.ToManyContRelationship \
        import ToManyContRelationship
    from Products.ZenRelations.ToManyRelationship \
        import ToManyRelationship
    from Products.ZenRelations.ToOneRelationship \
        import ToOneRelationship

    def descend(obj):
        """
        Function to determine whether or not to continue searching
        @param obj: object
        @type obj: object
        @return: True if we want to keep searching
        @rtype: boolean
        """
        return (
                isinstance(obj, ZenModelBase) or 
                isinstance(obj, ToManyContRelationship) or
                isinstance(obj, ToManyRelationship) or
                isinstance(obj, ToOneRelationship))

    def filter(obj):
        """
        Filter function to decide whether it's an object we
        want to know about or not.

        @param obj: object
        @type obj: object
        @return: True if we want to keep it
        @rtype: boolean
        """
        return isinstance(obj, ZenModelRM) and obj.id != "dmd"

    return getSubObjectsMemo(base, filter=filter, descend=descend)


def zenpathsplit(pathstring):
    """
    Split a zen path and clean up any blanks or bogus spaces in it

    @param pathstring: a path inside of ZENHOME
    @type pathstring: string
    @return: a path
    @rtype: string
    """
    path = pathstring.split("/")
    path = filter(lambda x: x, path)
    path = map(lambda x: x.strip(), path)
    return path



def zenpathjoin(pathar):
    """
    Build a zenpath in its string form

    @param pathstring: a path
    @type pathstring: string
    @return: a path
    @rtype: string
    """
    return "/" + "/".join(pathar)


def createHierarchyObj(root, name, factory, relpath="", llog=None):
    """
    Create a hierarchy object from its path we use relpath to skip down
    any missing relations in the path and factory is the constructor for 
    this object.

    @param root: root from which to start
    @type root: object
    @param name: path to object
    @type name: string
    @param factory: factory object to create
    @type factory: factory object
    @param relpath: relationship within which we will recurse as objects are created, if any
    @type relpath: object
    @param llog: unused
    @type llog: object
    @return: root object of a hierarchy
    @rtype: object
    """
    unused(llog)
    rootName = root.id
    for id in zenpathsplit(name):
        if id == rootName: continue
        if id == relpath or getattr(aq_base(root), relpath, False):
            root = getattr(root, relpath)
        if not getattr(aq_base(root), id, False):
            if id == relpath: 
                raise AttributeError("relpath %s not found" % relpath)
            log.debug("Creating object with id %s in object %s",id,root.getId())
            newobj = factory(id)
            root._setObject(id, newobj)
        root = getattr(root, id)

    return root


def getHierarchyObj(root, name, relpath=None):
    """
    Return an object using its path relations are optional in the path.

    @param root: root from which to start
    @type root: object
    @param name: path to object
    @type name: string
    @param relpath: relationship within which we will recurse as objects are created, if any
    @type relpath: object
    @return: root object of a hierarchy
    @rtype: object
    """
    for id in zenpathsplit(name):
        if id == relpath or getattr(aq_base(root), relpath, False):
            root = getattr(root, relpath)
        if not getattr(root, id, False):
            raise ZenPathError("Path %s id %s not found on object %s" %
                                (name, id, root.getPrimaryId()))
        root = getattr(root, id, None)

    return root
    


def basicAuthUrl(username, password, url):
    """
    Add the username and password to a url in the form
    http://username:password@host/path

    @param username: username
    @type username: string
    @param password: password
    @type password: string
    @param url: base URL to add username/password info
    @type url: string
    @return: URL with auth information incorporated
    @rtype: string
    """
    urlar = url.split('/')
    if not username or not password or urlar[2].find('@') > -1: 
        return url 
    urlar[2] = "%s:%s@%s" % (username, password, urlar[2])
    return "/".join(urlar)



def prepId(id, subchar='_'):
    """
    Make an id with valid url characters. Subs [^a-zA-Z0-9-_,.$\(\) ]
    with subchar.  If id then starts with subchar it is removed.

    @param id: user-supplied id
    @type id: string
    @return: valid id
    @rtype: string
    """
    _prepId = re.compile(r'[^a-zA-Z0-9-_,.$\(\) ]').sub
    _cleanend = re.compile(r"%s+$" % subchar).sub
    if id is None: 
        raise ValueError('Ids can not be None')
    if type(id) not in types.StringTypes:
        id = str(id)
    id = _prepId(subchar, id)
    while id.startswith(subchar):
        if len(id) > 1: id = id[1:]
        else: id = "-"
    id = _cleanend("",id)
    id = id.strip()
    return str(id)


def sendEmail(emsg, host, port=25, usetls=0, usr='', pwd=''):
    """
    Send an email.  Return a tuple:
    (sucess, message) where sucess is True or False.

    @param emsg: message to send
    @type emsg: string
    @param host: name of e-mail server
    @type host: string
    @param port: port number to communicate to the e-mail server
    @type port: integer
    @param usetls: boolean-type integer to specify whether to use TLS
    @type usetls: integer
    @param usr: username for TLS
    @type usr: string
    @param pwd: password for TLS
    @type pwd: string
    @return: (sucess, message) where sucess is True or False.
    @rtype: tuple
    """
    import smtplib
    fromaddr = emsg['From']
    toaddr = emsg['To'].split(', ')
    try:
        server = smtplib.SMTP(host, port)
        if usetls:
            server.ehlo()
            server.starttls()
            server.ehlo()
        if len(usr): server.login(usr, pwd)
        server.sendmail(fromaddr, toaddr, emsg.as_string())
        # Need to catch the quit because some servers using TLS throw an
        # EOF error on quit, so the email gets sent over and over
        try: server.quit()
        except: pass
    except (smtplib.SMTPException, socket.error):
        result = (False, '%s - %s' % tuple(sys.exc_info()[:2]))
    else:
        result = (True, '')
    return result
    
    
def sendPage(recipient, msg, pageCommand):
    """
    Send a page.  Return a tuple: (success, message) where
    sucess is True or False.

    @param recipient: name to where a page should be sent
    @type recipient: string
    @param msg: message to send
    @type msg: string
    @param pageCommand: command that will send a page
    @type pageCommand: string
    @return: (sucess, message) where sucess is True or False.
    @rtype: tuple
    """
    import subprocess
    env = dict(os.environ)
    env["RECIPIENT"] = recipient
    p = subprocess.Popen(pageCommand, 
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         shell=True,
                         env=env)
    p.stdin.write(msg)
    p.stdin.close()
    response = p.stdout.read()
    return (not p.wait(), response)
       

def zdecode(context, value):
    """
    Convert a string using the decoding found in zCollectorDecoding

    @param context: Zope object
    @type context: object
    @param value: input string
    @type value: string
    @return: converted string
    @rtype: string
    """
    if type(value) == type(''):
        decoding = getattr(context, 'zCollectorDecoding', 'latin-1')
        value = value.decode(decoding)
    return value


def localIpCheck(context, ip):
    """
    Test to see if an IP should not be included in the network map.
    Uses the zLocalIpAddresses to decide.

    @param context: Zope object
    @type context: object
    @param ip: IP address
    @type ip: string
    @return: regular expression match or None (if not found)
    @rtype: re match object
    """
    return re.search(getattr(context, 'zLocalIpAddresses', '^$'), ip) 

def localInterfaceCheck(context, intname):
    """
    Test to see if an interface should not be included in the network map.
    Uses the zLocalInterfaceNames to decide.

    @param context: Zope object
    @type context: object
    @param intname: network interface name
    @type intname: string
    @return: regular expression match or None (if not found)
    @rtype: re match object
    """
    return re.search(getattr(context, 'zLocalInterfaceNames', '^$'), intname)


def cmpClassNames(obj, classnames):
    """
    Check to see if any of an object's base classes 
    are in a list of class names. Like isinstance(), 
    but without requiring a class to compare against.

    @param obj: object
    @type obj: object
    @param classnames: class names
    @type classnames: list of strings
    @return: result of the comparison
    @rtype: boolean
    """
    finalnames = Set()
    x = [obj.__class__]
    while x:
        thisclass = x.pop()
        x.extend(thisclass.__bases__)
        finalnames.add(thisclass.__name__)
    return bool( Set(classnames).intersection(finalnames) )


def resequence(context, objects, seqmap, origseq, REQUEST):
    """
    Resequence a seqmap

    @param context: Zope object
    @type context: object
    @param objects: objects
    @type objects: list
    @param seqmap: sequence map
    @type seqmap: list
    @param origseq: sequence map
    @type origseq: list
    @param REQUEST: Zope REQUEST object
    @type REQUEST: Zope REQUEST object
    @return:
    @rtype: string
    """
    if seqmap and origseq:
        try:
            origseq = tuple([long(s) for s in origseq])
            seqmap = tuple([float(s) for s in seqmap])
        except ValueError:
            origseq = ()
            seqmap = ()
        orig = dict([(o.sequence, o) for o in objects])
        if origseq:
            for oldSeq, newSeq in zip(origseq, seqmap):
                orig[oldSeq].sequence = newSeq
    def sort(x):
        """
        @param x: unordered sequence items
        @type x: list
        @return: ordered sequence items
        @rtype: list
        """
        x = list(x)
        x.sort(lambda a, b: cmp(a.sequence, b.sequence))
        return x

    for i, obj in enumerate(sort(objects)):
        obj.sequence = i

    if REQUEST:
        return context.callZenScreen(REQUEST)
    

def cleanupSkins(dmd):
    """
    Prune out objects

    @param dmd: Device Management Database
    @type dmd: DMD object
    """
    ps = dmd.getPhysicalRoot().zport.portal_skins
    layers = ps._objects
    layers = filter(lambda x:getattr(ps, x['id'], False), layers)
    ps._objects = tuple(layers)


def edgesToXML(edges, start=()):
    """
    Convert edges to an XML file

    @param edges: edges
    @type edges: list
    @return: XML-formatted string
    @rtype: string
    """
    nodet = '<Node id="%s" prop="%s" icon="%s" color="%s"/>'
    edget = '<Edge fromID="%s" toID="%s"/>'
    xmlels = ['<Start name="%s" url="%s"/>' % start]
    nodeels = []
    edgeels = []
    for a, b in edges:
        node1 = nodet % (a[0], a[0], a[1], a[2])
        node2 = nodet % (b[0], b[0], b[1], b[2])
        edge1 = edget % (a[0], b[0])
        if node1 not in nodeels: nodeels.append(node1)
        if node2 not in nodeels: nodeels.append(node2)
        if edge1 not in edgeels: edgeels.append(edge1)

    xmlels.extend(nodeels)
    xmlels.extend(edgeels)
    xmldoc = "<graph>%s</graph>" % ''.join(list(xmlels))

    return xmldoc


def sane_pathjoin(base_path, *args ):
    """
    Joins paths in a saner manner than os.path.join()

    @param base_path: base path to assume everything is rooted from
    @type base_path: string
    @param *args: path components starting from $ZENHOME
    @type *args: strings
    @return: sanitized path
    @rtype: string
    """
    path = base_path
    if args:
        # Hugely bizarre (but documented!) behaviour with os.path.join()
        # >>> import os.path
        # >>> os.path.join( '/blue', 'green' )
        # '/blue/green'
        # >>> os.path.join( '/blue', '/green' )
        # '/green'
        # Work around the brain damage...
        base = args[0]
        if base.startswith( base_path ):
            path_args = [ base ] + [a.strip('/') for a in args[1:] if a != '' ]
        else:
            path_args = [a.strip('/') for a in args if a != '' ]

        # Empty strings get thrown out so we may not have anything
        if len(path_args) > 0:
            # What if the user splits up base_path and passes it in?
            pathological_case = os.path.join( *path_args )
            if pathological_case.startswith( base_path ):
                pass

            elif not base.startswith( base_path ):
                path_args.insert( 0, base_path )

            # Note: passing in a list to os.path.join() returns a list,
            #       again completely unlike string join()
            path = os.path.join( *path_args )

    # os.path.join( '/blue', '' ) returns '/blue/' -- egads!
    return path.rstrip('/')


def zenPath(*args):
    """
    Return a path relative to $ZENHOME specified by joining args.  The path
    is not guaranteed to exist on the filesystem.
    
    >>> import os
    >>> zenHome = os.environ['ZENHOME']
    >>> zenPath() == zenHome
    True
    >>> zenPath( '' ) == zenHome
    True
    >>> zenPath('Products') == os.path.join(zenHome, 'Products')
    True
    >>> zenPath('/Products/') == zenPath('Products')
    True
    >>> 
    >>> zenPath('Products', 'foo') == zenPath('Products/foo')
    True

    # NB: The following is *NOT* true for os.path.join()
    >>> zenPath('/Products', '/foo') == zenPath('Products/foo')
    True
    >>> zenPath(zenPath('Products')) == zenPath('Products')
    True
    >>> zenPath(zenPath('Products'), 'orange', 'blue' ) == zenPath('Products', 'orange', 'blue' )
    True

    # Pathological case
    # NB: need to expand out the array returned by split()
    >>> zenPath() == zenPath( *'/'.split(zenPath()) )
    True

    @param *args: path components starting from $ZENHOME
    @type *args: strings
    @todo: determine what the correct behaviour should be if $ZENHOME is a symlink!
    """
    zenhome = os.environ.get( 'ZENHOME', '' )

    path = sane_pathjoin( zenhome, *args )

    #test if ZENHOME based path exists and if not try bitrock-style path.
    #if neither exists return the ZENHOME-based path
    if not os.path.exists(path):
        brPath = os.path.realpath(os.path.join(zenhome, '..', 'common'))
        testPath = sane_pathjoin(brPath, *args)
        if(os.path.exists(testPath)):
            path = testPath
    return path


def zopePath(*args):
    """
    Similar to zenPath() except that this constructs a path based on
    ZOPEHOME rather than ZENHOME.  This is useful on the appliance.
    If ZOPEHOME is not defined or is empty then return ''.
    NOTE: A non-empty return value does not guarantee that the path exists,
    just that ZOPEHOME is defined.
    
    >>> import os
    >>> zopeHome = os.environ.setdefault('ZOPEHOME', '/something')
    >>> zopePath('bin') == os.path.join(zopeHome, 'bin')
    True
    >>> zopePath(zopePath('bin')) == zopePath('bin')
    True
    
    @param *args: path components starting from $ZOPEHOME
    @type *args: strings
    """
    zopehome = os.environ.get('ZOPEHOME', '')
    return sane_pathjoin( zopehome, *args )


def binPath(fileName):
    """
    Search for the given file in a list of possible locations.  Return
    either the full path to the file or '' if the file was not found.
    
    >>> len(binPath('zenoss')) > 0
    True
    >>> len(binPath('zeoup.py')) > 0
    True
    >>> len(binPath('check_http')) > 0
    True
    >>> binPath('Idontexistreally') == ''
    True

    @param fileName: name of executable
    @type fileName: string
    @return: path to file or '' if not found
    @rtype: string
    """
    # bin and libexec are the usual suspect locations.
    # ../common/bin and ../common/libexec are additional options for bitrock
    # $ZOPEHOME/bin is an additional option for appliance
    for path in (zenPath(d, fileName) for d in (
                'bin', 'libexec', '../common/bin', '../common/libexec')):
        if os.path.isfile(path):
            return path
    path = zopePath('bin', fileName)
    if os.path.isfile(path):
        return path
    return ''


def extractPostContent(REQUEST):
    """
    IE puts the POST content in one place in the REQUEST object, and Firefox in
    another. Thus we need to try both.

    @param REQUEST: Zope REQUEST object
    @type REQUEST: Zope REQUEST object
    @return: POST content
    @rtype: string
    """
    try:
        try:
            # Firefox
            result = REQUEST._file.read()
        except:
            # IE         
            result = REQUEST.form.keys()[0]
    except: result = ''
    return result


def unused(*args):
    """
    A no-op function useful for shutting up pychecker

    @param *args: arbitrary arguments
    @type *args: objects
    @return: count of the objects
    @rtype: integer
    """
    return len(args)


def isXmlRpc(REQUEST):
    """
    Did we receive a XML-RPC call?

    @param REQUEST: Zope REQUEST object
    @type REQUEST: Zope REQUEST object
    @return: True if REQUEST is an XML-RPC call
    @rtype: boolean
    """
    if REQUEST and REQUEST['CONTENT_TYPE'].find('xml') > -1:
        return True
    else:
        return False


def setupLoggingHeader(context, REQUEST):
    """
    Extract out the 2nd outermost table

    @param context: Zope object
    @type context: Zope object
    @param REQUEST: Zope REQUEST object
    @type REQUEST: Zope REQUEST object
    @return: response
    @rtype: string
    """
    response = REQUEST.RESPONSE
    dlh = context.discoverLoggingHeader()
    idx = dlh.rindex("</table>")
    dlh = dlh[:idx]
    idx = dlh.rindex("</table>")
    dlh = dlh[:idx]
    response.write(str(dlh[:idx]))

    return setWebLoggingStream(response)


def executeCommand(cmd, REQUEST):
    """
    Execute the command and return the output

    @param cmd: command to execute
    @type cmd: string
    @param REQUEST: Zope REQUEST object
    @type REQUEST: Zope REQUEST object
    @return: result of executing the command
    @rtype: string
    """
    xmlrpc = isXmlRpc(REQUEST)
    result = 0
    try:
        if REQUEST:
            response = REQUEST.RESPONSE
        else:
            response = sys.stdout
        log.info('Executing command: %s' % ' '.join(cmd))
        f = Popen4(cmd)
        while 1:
            s = f.fromchild.readline()
            if not s: 
                break
            elif response:
                response.write(s)
                response.flush()
            else:
                log.info(s)
    except (SystemExit, KeyboardInterrupt): 
        if xmlrpc: return 1
        raise
    except ZentinelException, e:
        if xmlrpc: return 1
        log.critical(e)
    except: 
        if xmlrpc: return 1
        raise
    else:
        result = f.wait()
        result = int(hex(result)[:-2], 16)
    return result


def ipsort(a, b):
    """
    Compare (cmp()) a + b's IP addresses
    These addresses may contain subnet mask info.

    @param a: IP address
    @type a: string
    @param b: IP address
    @type b: string
    @return: result of cmp(a.ip,b.ip)
    @rtype: boolean
    """
    # Use 0.0.0.0 instead of blank string
    if not a: a = "0.0.0.0"
    if not b: b = "0.0.0.0"
    
    # Strip off netmasks
    a, b = map(lambda x:x.rsplit("/")[0], (a, b))
    return cmp(*map(socket.inet_aton, (a, b)))


def unsigned(v):
    """
    Convert negative 32-bit values into the 2's complement unsigned value

    >>> str(unsigned(-1))
    '4294967295'
    >>> unsigned(1)
    1L
    >>> unsigned(1e6)
    1000000L
    >>> unsigned(1e10)
    10000000000L

    @param v: number
    @type v: negative 32-bit number
    @return: 2's complement unsigned value
    @rtype: unsigned int
    """
    v = long(v)
    if v < 0:
        import ctypes
        return int(ctypes.c_uint32(v).value)
    return v


def executeStreamCommand(cmd, writefunc, timeout=30):
    """
    Execute cmd in the shell and send the output to writefunc.

    @param cmd: command to execute
    @type cmd: string
    @param writefunc: output function
    @type writefunc: function
    @param timeout: maxium number of seconds to wait for the command to execute
    @type timeout: number
    """
    child = popen2.Popen4(cmd)
    flags = fcntl.fcntl(child.fromchild, fcntl.F_GETFL)
    fcntl.fcntl(child.fromchild, fcntl.F_SETFL, flags | os.O_NDELAY)
    pollPeriod = 1
    endtime = time.time() + timeout
    firstPass = True
    while time.time() < endtime and (
        firstPass or child.poll()==-1):
        firstPass = False
        r,w,e = select.select([child.fromchild],[],[],pollPeriod)
        if r:
            t = child.fromchild.read()
            if t:
                writefunc(t)
    if child.poll()==-1:
        writefunc('Command timed out')
        import signal
        os.kill(child.pid, signal.SIGKILL)


def monkeypatch(target):
    """
    A decorator to patch the decorated function into the given class.

        >>> @monkeypatch('Products.ZenModel.DataRoot.DataRoot')
        ... def do_nothing_at_all(self):
        ...     print "I do nothing at all."
        ...
        >>> from Products.ZenModel.DataRoot import DataRoot
        >>> hasattr(DataRoot, 'do_nothing_at_all')
        True
        >>> DataRoot('dummy').do_nothing_at_all()
        I do nothing at all.


    @param target: class
    @type target: class object
    @return: decorator function return
    @rtype: function
    """
    if isinstance(target, basestring):
        mod, klass = target.rsplit('.', 1)
        target = importClass(mod, klass)
    def patcher(func):
        setattr(target, func.__name__, func)
        return func
    return patcher


from Products.ZenUtils.json import json as _json
def json(f):
    """
    Decorator that serializes the return value of the decorated function as
    JSON.

    Use of the C{ZenUtils.Utils.json} decorator is deprecated. Please import 
    from C{ZenUtils.json}. 

        >>> @json
        ... def f():
        ...     return (dict(a=1L), u"123", 123)
        ...
        >>> print f()
        [{"a": 1}, "123", 123]

    @param f: class
    @type f: class object
    @return: decorator function return
    @rtype: function
    @deprecated: import from Products.ZenWidgets.json
    """
    warnings.warn("Use of the ZenUtils.Utils.json decorator is deprecated. " 
                  "Please import from Products.ZenUtils.json", 
                  DeprecationWarning) 
    return _json(f) 

def formreq(f): 
    """ 
    Decorator to pass in request.form information as arguments to a method. 

    These are intended to decorate methods of BrowserViews. 

    @param f: class
    @type f: class object
    @return: decorator function return
    @rtype: function
    """ 
    def inner(self, *args, **kwargs): 
        """
        Inner portion of the decorator

        @param *args: arguments
        @type *args: possible list
        @param **kwargs: keyword arguments
        @type **kwargs: possible list
        @return: decorator function return
        @rtype: function
        """
        kwargs.update(self.request.form) 
        # Get rid of useless Zope thing that appears when no querystring 
        if kwargs.has_key('-C'): del kwargs['-C'] 
        # Get rid of kw used to prevent browser caching 
        if kwargs.has_key('_dc'): del kwargs['_dc'] 
        return f(self, *args, **kwargs) 

    return inner


class Singleton(type):
    """
    Metaclass that ensures only a single instance of a class is ever created.

    This is accomplished by storing the first instance created as an attribute
    of the class itself, then checking that attribute for later constructor
    calls.
    """
    def __init__(cls, *args, **kwargs):
        super(Singleton, cls).__init__(*args, **kwargs)
        cls._singleton_instance = None

    def __call__(cls, *args, **kwargs):
        if cls._singleton_instance is None:
            cls._singleton_instance = super(
                Singleton, cls).__call__(*args, **kwargs)
        return cls._singleton_instance


def readable_time(seconds, precision=1):
    """
    Convert some number of seconds into a human-readable string.

    @param t: The number of seconds to convert
    @type t: int
    @param precision: The maximum number of time units to include.
    @type t: int
    @rtype: str

        >>> readable_time(1)
        '1 second'
        >>> readable_time(60)
        '1 minute'
        >>> readable_time(60*60*3+12)
        '3 hours'
        >>> readable_time(60*60*3+12, 2)
        '3 hours 12 seconds'

    """
    names = ('year', 'month', 'week', 'day', 'hour', 'minute', 'second')
    mults = (60*60*24*365, 60*60*24*30, 60*60*24*7, 60*60*24, 60*60, 60, 1)
    result = []
    remaining = abs(seconds)
    for name, div in zip(names, mults):
        num = Decimal(str(math.floor(remaining/div)))
        remaining -= num*div
        num = int(num)
        if num:
            result.append('%d %s%s' %(num, name, num>1 and 's' or ''))
        if len(result)==precision:
            break
    return ' '.join(result)


def relative_time(t, precision=1, cmptime=None):
    """
    Return a human-readable string describing time relative to C{cmptime}
    (defaulted to now).

    @param t: The time to convert, in seconds since the epoch.
    @type t: int
    @param precision: The maximum number of time units to include.
    @type t: int
    @param cmptime: The time from which to compute the difference, in seconds
    since the epoch
    @type cmptime: int
    @rtype: str

        >>> relative_time(time.time() - 60*10)
        '10 minutes ago'
        >>> relative_time(time.time() - 60*10-3, precision=2)
        '10 minutes 3 seconds ago'
        >>> relative_time(time.time() - 60*60*24*10, precision=2)
        '1 week 3 days ago'
        >>> relative_time(time.time() - 60*60*24*365-1, precision=2)
        '1 year 1 second ago'
        >>> relative_time(time.time() + 60*60*24*7*2)
        'in 2 weeks'

    """
    if cmptime is None:
        cmptime = time.time()
    seconds = Decimal(str(t - cmptime))
    result = readable_time(seconds, precision)
    if seconds < 0:
        result += ' ago'
    else:
        result = 'in ' + result
    return result


EXIT_CODE_MAPPING = {
    0:'Success',
    1:'General error',
    2:'Misuse of shell builtins',
    126:'Command invoked cannot execute, permissions problem or command is not an executable',
    127:'Command not found',
    128:'Invalid argument to exit, exit takes only integers in the range 0-255',
    130:'Fatal error signal: 2, Command terminated by Control-C'
}

def getExitMessage(exitCode):
    """
    Return a nice exit message that corresponds to the given exit status code

    @param exitCode: process exit code
    @type exitCode: integer
    @return: human-readable version of the exit code
    @rtype: string
    """
    if exitCode in EXIT_CODE_MAPPING.keys():
        return EXIT_CODE_MAPPING[exitCode]
    elif exitCode >= 255:
        return 'Exit status out of range, exit takes only integer arguments in the range 0-255'
    elif exitCode > 128:
        return 'Fatal error signal: %s' % (exitCode-128)
    return 'Unknown error code: %s' % exitCode

