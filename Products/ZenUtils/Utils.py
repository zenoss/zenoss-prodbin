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

General Utility function module

$Id: Utils.py,v 1.15 2004/04/04 02:22:38 edahl Exp $"""

__version__ = "$Revision: 1.15 $"[11:-2]

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

    def __init__(self):
        logging.Formatter.__init__(self, 
        """<tr class="loggingRow">
        <td>%(asctime)s</td><td>%(levelname)s</td>
        <td>%(name)s</td><td>%(message)s</td>
        </tr>
        """,
        "%Y-%m-%d %H:%M:%S")

    def formatException(self, exc_info):
        exc = logging.Formatter.formatException(self,exc_info)
        return """<tr class="tablevalues"><td colspan="4">%s</td></tr>""" % exc


def setWebLoggingStream(stream):
    """Setup logging to log to a browser using a request object."""
    handler = logging.StreamHandler(stream)
    handler.setFormatter(HtmlFormatter())
    rlog = logging.getLogger()
    rlog.addHandler(handler)
    rlog.setLevel(logging.ERROR)
    zlog = logging.getLogger("zen")
    zlog.setLevel(logging.INFO)
    return handler


def clearWebLoggingStream(handler):
    """Clear our web logger."""
    rlog = logging.getLogger()
    rlog.removeHandler(handler)


def convToUnits(numb, divby=1024.0):
    """Convert a number to its human readable form. ie: 4GB, 4MB, etc.
    """
    units = ('B','KB','MB','GB','TB','PB')
    numb = float(numb)
    sign = 1
    if numb < 0:
        numb = abs(numb)
        sign = -1
    for unit in units:
        if numb < divby: break
        numb /= divby
    return "%.1f%s" % (numb * sign, unit)
        

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


def getObjByPath(base, path, restricted=0):
    """Get a Zope object by its path (e.g. '/Devices/Server/Linux').
       Mostly a stripdown of unrestrictedTraverse method from Zope 2.8.8.
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
            raise Unauthorized, base

    obj = base
    while path:
        name = path_pop()

        if name[0] == '_':
            # Never allowed in a URL.
            raise NotFound, name

        if name == '..':
            next = aq_parent(obj)
            if next is not _none:
                if restricted and not securityManager.validate(
                    obj, obj,name, next):
                    raise Unauthorized, name
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
                    raise Unauthorized, name
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
                    raise NotFound, name
                if restricted and not securityManager.validate(
                    obj, obj, _none, next):
                    raise Unauthorized, name
        obj = next
    return obj



def checkClass(myclass, className):
    """perform issubclass using class name as string"""
    if myclass.__name__ == className:
        return 1
    for mycl in myclass.__bases__:
        if checkClass(mycl, className):
            return 1


def lookupClass(productName, classname=None):
        """look in sys.modules for our class"""
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
    """Import a class from the module given.
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
        raise ImportError("failed importing class %s from module %s" % (
                            classname, modulePath))


def cleanstring(value):
    """take the trailing \x00 off the end of a string"""
    if type(value) in types.StringTypes:
        value = value.split('\0')[0]
    return value


def getSubObjects(base, filter=None, decend=None, retobjs=None):
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
    from Products.ZenModel.ZenModelRM import ZenModelRM
    from Products.ZenModel.ZenModelBase import ZenModelBase
    from Products.ZenRelations.ToManyContRelationship \
        import ToManyContRelationship
    from Products.ZenRelations.ToManyRelationship \
        import ToManyRelationship
    from Products.ZenRelations.ToOneRelationship \
        import ToOneRelationship
    def decend(obj):
        return (
                isinstance(obj, ZenModelBase) or 
                isinstance(obj, ToManyContRelationship) or
                isinstance(obj, ToManyRelationship) or
                isinstance(obj, ToOneRelationship))
    def filter(obj):
        return isinstance(obj, ZenModelRM) and obj.id != "dmd"
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
                    relpath=None, lastrelpath=None, llog=None):
    """build and return the path to an object 
    based on a hierarchical name (ex /Mail/Mta) relative
    to the root passed in.  If lastfactory is passed the leaf object
    will be created with it instead of factory. 
    relpath is the relationship within which we will recurse as
    objects are created.  Having the relationship in the path passed
    is optional."""
    unused(llog)
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
                    log.debug("creating object with id %s in relation %s",
                                id, relobj.getId())
                    factory(relobj, id)
                nextroot = relobj._getOb(id)
            else:
                log.debug("creating object with id %s", id)
                factory(root, id)
                nextroot = root._getOb(id)
        root = nextroot
    return root


def createHierarchyObj(root, name, factory, relpath="", llog=None):
    """
    Create a hierarchy object from its path we use relpath to skip down
    any missing relations in the path and factory is the constructor for 
    this object.
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



def prepId(id, subchar='_'):
    """Make an id with valid url characters. Subs [^a-zA-Z0-9-_,.$\(\) ]
    with subchar.  If id then starts with subchar it is removed.
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
    ''' Send an email.  Return a tuple:
    (sucess, message) where sucess is True or False.
    '''
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
    ''' Send a page.  Return a tuple: (success, message) where
    sucess is True or False.
    '''
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
    if type(value) == type(''):
        decoding = getattr(context, 'zCollectorDecoding', 'latin-1')
        value = value.decode(decoding)
    return value


def localIpCheck(context, ip):
    """Test to see if ip it should not be included in the network map."""
    return re.search(getattr(context, 'zLocalIpAddresses', '^$'), ip) 

def localInterfaceCheck(context, intname):
    """Test to see if ips on an in should not be included in the network map."""
    return re.search(getattr(context, 'zLocalInterfaceNames', '^$'), intname)


def cmpClassNames(obj, classnames):
    """ Check to see if any of an object's base classes 
        are in a list of class names. Like isinstance(), 
        but without requiring a class to compare against.
    """
    finalnames = Set()
    x = [obj.__class__]
    while x:
        thisclass = x.pop()
        x.extend(thisclass.__bases__)
        finalnames.add(thisclass.__name__)
    return bool( Set(classnames).intersection(finalnames) )

def resequence(context, objects, seqmap, origseq, REQUEST):
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
        x = list(x)
        x.sort(lambda a, b: cmp(a.sequence, b.sequence))
        return x
    for i, obj in enumerate(sort(objects)):
        obj.sequence = i
    if REQUEST:
        return context.callZenScreen(REQUEST)
    
def cleanupSkins(dmd):
    ps = dmd.getPhysicalRoot().zport.portal_skins
    layers = ps._objects
    layers = filter(lambda x:getattr(ps, x['id'], False), layers)
    ps._objects = tuple(layers)

def edgesToXML(edges, start=()):
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

def zenPath(*args):
    """
    Return a path relative to $ZENHOME specified by joining args.  The path
    is not guaranteed to exist on the filesystem.
    
    >>> import os
    >>> zenHome = os.environ['ZENHOME']
    >>> zenPath() == zenHome
    True
    >>> zenPath('Products') == os.path.join(zenHome, 'Products')
    True
    >>> zenPath('/Products/') == zenPath('Products')
    True
    >>> 
    >>> zenPath('Products', 'foo') == zenPath('Products/foo')
    True

    """
    args = [a.strip('/') for a in args]
    path = os.path.join(os.environ['ZENHOME'], *args)
    #test if ZENHOME based path exists and if not try bitrock style path.
    #if neither exists return the ZENHOME based path
    if(not os.path.exists(path)):
        testPath = os.path.join(os.environ['ZENHOME'], "..", "common", *args)
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
    
    """
    args = [a.strip('/') for a in args]
    if os.environ.get('ZOPEHOME', ''):
        return os.path.join(os.environ['ZOPEHOME'], *args)
    return ''

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

def unused(*args):                      # useful for shutting up pychecker
    return len(args)


def isXmlRpc(REQUEST):
    if REQUEST and REQUEST['CONTENT_TYPE'].find('xml') > -1:
        return True
    else:
        return False

def setupLoggingHeader(context, REQUEST):
    response = REQUEST.RESPONSE
    dlh = context.discoverLoggingHeader()
    idx = dlh.rindex("</table>")
    dlh = dlh[:idx]
    idx = dlh.rindex("</table>")
    dlh = dlh[:idx]
    response.write(str(dlh[:idx]))
    return setWebLoggingStream(response)


def executeCommand(cmd, REQUEST):
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
    # Strip off netmasks
    a, b = map(lambda x:x.rsplit("/")[0], (a, b))
    return cmp(*map(socket.inet_aton, (a, b)))


def unsigned(v):
    '''Convert negative 32-bit values into the 2s compliment unsigned value

    >>> unsigned(-1)
    4294967295L
    >>> unsigned(1)
    1L
    >>> unsigned(1e6)
    1000000L
    >>> unsigned(1e10)
    10000000000L
    '''
    v = long(v)
    if v < 0:
        import ctypes
        return int(ctypes.c_uint32(v).value)
    return v


def executeStreamCommand(cmd, writefunc, timeout=30):
    """
    Execute cmd in the shell and send the output to writefunc.
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

    """
    if isinstance(target, basestring):
        mod, klass = target.rsplit('.', 1)
        target = importClass(mod, klass)
    def patcher(func):
        setattr(target, func.__name__, func)
        return func
    return patcher

