#################################################################
#
#   Copyright (c) 2003 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""ImportRM

Export RelationshipManager objects from a zope database

$Id: ImportRM.py,v 1.3 2003/10/03 16:16:01 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

import sys

import Zope
Zope.startup()

from xml.sax import make_parser
from xml.sax.handler import ContentHandler

from Acquisition import aq_base

from DateTime import DateTime

from Products.ConfUtils.ZCmdBase import ZCmdBase
from Products.ConfUtils.Utils import lookupClass

from Products.RelationshipManager.Exceptions import *

class ImportRM(ZCmdBase, ContentHandler):

    def __init__(self):
        ZCmdBase.__init__(self)
        
        self.links = {}
        self.blocklinks = {}
        self.curobjstack = []
        self.curstatestack = []
        self.curattrsstack = []
        self.objectnumber = 0
        self.firstprop = 1

        if not self.options.infile:
            self.infile = sys.stdin
        else:
            self.infile = open(self.options.infile, 'r')


    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZCmdBase.buildOptions(self)

        self.parser.add_option('-i', '--infile',
                    dest="infile",
                    help="input file for import default is stdin")
        
        self.parser.add_option('-x', '--commitCount',
                    dest='commitCount',
                    default=20,
                    type="int",
                    help='how many lines should be loaded before commit')

        self.parser.add_option('-n', '--noCommit',
                    dest='noCommit',
                    action="store_true",
                    default=0,
                    help='Do not store changes to the Dmd (for debugging)')


    def loadDatabase(self):
        """top level of this loader makes a parser and 
        passes itself has a content handler"""
        parser = make_parser()
        parser.setContentHandler(self)
        parser.parse(self.infile)
        self.infile.close()
  

    def commit(self):
        trans = get_transaction()
        trans.note('Import from file %s using %s' 
                        % (self.options.infile, 
                            self.__class__.__name__))
        trans.commit()


    def startElement(self, name, attrs):
        self.curstatestack.append(name)
        self.curattrsstack.append(attrs)
        if name == 'object':
            obj = self.createObject(attrs)
            self.curobjstack.append(obj)


    def endElement(self, name):
        if name == 'object': 
            self.curobjstack.pop()
            self.objectnumber += 1
            if (not self.options.noCommit 
                and not self.objectnumber % self.options.commitCount):
                self.commit()
                self.app._p_jar.sync()
        elif name == 'property':
            self.firstprop = 1
        elif name == 'objects':
            self.log.info("Processing links")
            self.processLinks()
            if not self.options.noCommit:
                self.commit()
            self.log.info("Loaded %d objects into database" % self.objectnumber)
        if len(self.curstatestack):
            self.curstatestack.pop()
            self.curattrsstack.pop()
       

    def characters(self, chars):    
        if not len(self.curobjstack): return
        obj = self.curobjstack[-1]
        chars = str(chars.strip())
        if not chars: return
        parentattrs = {}
        if len(self.curattrsstack) > 1:
            parentattrs = self.curattrsstack[-2]
        attrs = self.curattrsstack[-1]
        state = self.curstatestack[-1]
        if state == 'link':
            relname = str(parentattrs.get('id'))
            self.addLink(obj, relname, chars)
        elif state == 'toone':
            relname = str(attrs.get('id')) 
            self.addLink(obj, relname, chars)
        elif state == 'value':
            self.setProperty(obj, parentattrs, chars)


    def createObject(self, attrs):
        """create an object and set it into its container"""
        modname = str(attrs.get('module'))
        classname = str(attrs.get('class'))
        fullid = str(attrs.get('id'))
        obj = self.getDmdObj(fullid)
        if obj:
            self.log.warn("Object %s already exists skipping" % fullid)
            return obj
        klass = lookupClass(modname, classname)
        id = fullid.split('/')[-1]
        obj = klass(id)
        contname = '/'.join(fullid.split('/')[:-1])
        container = self.getDmdObj(contname)
        if not container: 
            raise ObjectNotFound, "Object %s not found" % contname
        container._setObject(obj.id, obj) 
        obj = container._getOb(obj.id)
        self.log.debug("Added object %s to database" % 
                            obj.getPrimaryId())
        if container.meta_type == "To Many Relationship":
            pobject = self.curobjstack[-1] 
            self.removeLink(pobject, container.id, 
                        obj.getPrimaryId())
        return obj


    def setProperty(self, obj, attrs, value):
        """set the value of a property
        if property doesn't exist add it to _properties"""

        name = str(attrs.get('id'))
        proptype = str(attrs.get('type'))

        self.log.debug("setting object %s att %s type %s value %s" 
                            % (obj.id, name, proptype, value))

        if not hasattr(aq_base(obj), name):
            self.log.debug("updated _properties for attribute %s" % name)
            obj._properties = obj._properties + (self.makePropSchema(attrs),)

        if (proptype == 'int'
            or proptype == 'boolean'):
            value = int(value)
        elif proptype == 'long':
            value = long(value)
        elif proptype == 'float':
            value = float(value)
        elif proptype == 'date':
            value = DateTime(value)
        elif proptype == 'lines':
            if self.firstprop:
                curvalue = []
            else:
                curvalue = list(getattr(obj, name, []))
            curvalue.append(value)
            value = curvalue
            obj._p_changed = 1
        else:
            value = str(value)

        if attrs.has_key('setter'):
            settername = str(attrs.get('setter'))
            setter = getattr(obj, settername, None)
            if not setter:
                self.log.warning("setter %s for property %s doesn't exist"
                                    % (settername, name))
                return
            if not callable(setter):
                self.log.warning("setter %s for property %s not callable"
                                    % (settername, name))
                return
            setter(value)
        else:
            setattr(obj, name, value) 
        self.firstprop = 0 


    def makePropSchema(self, attrs):
        """convert Attributes object to dictionary"""
        schema = {}
        for key in attrs.keys():
            schema[str(key)] = str(attrs[key])
        return schema
        
    
    def addLink(self, obj, relname, link):
        """build list of links to form after all objects have been created
        make sure that we don't add other side of a bidirectional relation"""
        key = obj.relationKey(relname, link)
        if not self.links.has_key(key):
            self.links[key] = relname


    def removeLink(self, obj, relname, link):
        key = obj.relationKey(relname, link)
        self.blocklinks[key] = relname

    
    def processLinks(self):
        """walk through all the links that we saved and link them up"""
        for key, relname in self.links.items():
            if self.blocklinks.has_key(key): continue
            id1, r1, id2, r2 = key.split('|')
            self.log.debug("Linking object %s relation %s to object %s"
                            % (id1, id2, r1))
            obj1 = self.getDmdObj(id1)
            if not obj1:
                self.log.warn(
                    'While linking object %s relation %s' % (id1, r1) +
                    ' to object %s relation %s' % (id2, r2) +
                    ' object %s was not found' % id1)
                continue
            obj2 = self.getDmdObj(id2)
            if not obj2:
                self.log.warn(
                    'While linking object %s relation %s' % (id1, r1) +
                    ' to object %s relation %s' % (id2, r2) +
                    ' object %s was not found' % id2)
                continue
            try:
                obj1.addRelation(r1, obj2)
            except RelationshipExistsError:
                pass
            except:
                self.log.exception(
                    "Linking object %s relation %s to object %s failed"
                            % (id1, id2, relname))


if __name__ == '__main__':
    im = ImportRM()
    im.loadDatabase()
