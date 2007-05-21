#!/usr/bin/env python
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

__doc__="""ImportRM

Export RelationshipManager objects from a zope database

$Id: ImportRM.py,v 1.3 2003/10/03 16:16:01 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

import sys
import os
import types
import urllib2
import transaction
from urlparse import urlparse
from xml.sax import make_parser, saxutils
from xml.sax.handler import ContentHandler
import zipfile
from tempfile import TemporaryFile

from Acquisition import aq_base
from zExceptions import NotFound

from DateTime import DateTime

from Products.ZenUtils import Security
from Products.ZenUtils.CmdBase import CmdBase
from Products.ZenUtils.Utils import importClass
from Products.ZenUtils.Utils import getObjByPath

from Products.ZenRelations.Exceptions import *

if not os.environ.has_key('ZENHOME'):
    raise SysemExit("ERROR: ZENHOME envrionment variable not set")
zenhome = os.environ['ZENHOME']


class ImportRM(CmdBase, ContentHandler):

    rootpath = ""

    def __init__(self):
        CmdBase.__init__(self)
        zopeconf = os.path.join(zenhome, "etc/zope.conf")
        import Zope2
        Zope2.configure(zopeconf)
        self.app = Zope2.app()

    #def setupLogging(self): pass

    def context(self):
        return self.objstack[-1]


    def cleanattrs(self, attrs):
        myattrs = {}
        for key, val in attrs.items():
            try:
                myattrs[key] = str(val)
            except UnicodeEncodeError:
                myattrs[key] = unicode(val)
        return myattrs

        
    def startElement(self, name, attrs):
        attrs = self.cleanattrs(attrs)
        self.state = name
        self.log.debug("tag %s, context %s", name, self.context().id)
        if name == 'object':
            obj = self.createObject(attrs)
            if (not self.options.noindex  
                and hasattr(aq_base(obj), 'reIndex')
                and not self.rootpath):
                self.rootpath = obj.getPrimaryId()
            self.objstack.append(obj)
        elif name == 'tomanycont' or name == 'tomany':
            self.objstack.append(self.context()._getOb(attrs['id']))
        elif name == 'toone':
            relname = attrs.get('id')
            self.log.debug("toone %s, on object %s", relname, self.context().id)
            rel = getattr(aq_base(self.context()),relname)
            objid = attrs.get('objid')
            self.addLink(rel, objid)
        elif name == 'link':
            self.addLink(self.context(), attrs['objid'])
        elif name == 'property':
            self.curattrs = attrs


    def endElement(self, name):
        if name in ('object', 'tomany', 'tomanycont'):
            obj = self.objstack.pop()
            if self.rootpath == obj.getPrimaryId():
                self.log.info("calling reIndex %s", obj.getPrimaryId())
                obj.reIndex()
                self.rootpath = ""
        elif name == 'objects':
            self.log.info("End loading objects")
            self.log.info("Processing links")
            self.processLinks()
            if not self.options.noCommit:
                self.commit()
            self.log.info("Loaded %d objects into database" % self.objectnumber)
        elif name == 'property':
            self.setProperty(self.context(), self.curattrs, self.charvalue)
            self.charvalue = ""
       

    def characters(self, chars):
        self.charvalue += saxutils.unescape(chars)


    def createObject(self, attrs):
        """create an object and set it into its container"""
        id = attrs.get('id')
        obj = None
        try:
            if callable(self.context().id):
                obj = getObjByPath(self.app, id)
            else:
                obj = self.context()._getOb(id)
        except (KeyError, AttributeError, NotFound): pass
        if obj is None:
            klass = importClass(attrs.get('module'), attrs.get('class'))
            if id.find("/") > -1:
                contextpath, id = os.path.split(id)
                self.objstack.append(
                    getObjByPath(self.context(), contextpath))
            obj = klass(id)
            self.context()._setObject(obj.id, obj)
            obj = self.context()._getOb(obj.id)
            self.objectnumber += 1
            if self.objectnumber % 5000 == 0: transaction.savepoint()
            self.log.debug("Added object %s to database" % obj.getPrimaryId())
        else:
            self.log.warn("Object %s already exists skipping" % id)
        return obj


    def setProperty(self, obj, attrs, value):
        """Set the value of a property on an object.
        """
        name = attrs.get('id')
        proptype = attrs.get('type')
        setter = attrs.get("setter",None)
        label = attrs.get('label', None)
        visible = attrs.get('visible', True)
        selvar = attrs.get('select_variable', '')
        self.log.debug("setting object %s att %s type %s value %s" 
                            % (obj.id, name, proptype, value))
        value = value.strip()
        #if setter == 'setIpAddresses': import pdb;pdb.set_trace()
        if proptype == 'selection':
            alist = getattr(obj, selvar, [])
            if (len(alist) == 0 or 
                (len(alist) > 0 and type(alist[0]) in types.StringTypes)):
                proptype = 'string'
        if proptype == "date":
            try: value = float(value)
            except ValueError: pass
            value = DateTime(value)
        elif proptype != "string" and proptype != 'text':
            try: value = eval(value)
            except SyntaxError: pass
        if not obj.hasProperty(name):
            obj._setProperty(name, value, type=proptype, label=label,
                            visible=visible, setter=setter)
        else:
            obj._updateProperty(name, value)


    def addLink(self, rel, objid):
        """build list of links to form after all objects have been created
        make sure that we don't add other side of a bidirectional relation"""
        self.links.append((rel.getPrimaryId(), objid))


    def processLinks(self):
        """walk through all the links that we saved and link them up"""
        for relid, objid in self.links:
            try:
                self.log.debug("Linking relation %s to object %s",
                                relid,objid)
                rel = getObjByPath(self.app, relid)
                obj = getObjByPath(self.app, objid)
                if not rel.hasobject(obj):
                    rel.addRelation(obj)
            except:
                self.log.critical(
                    "Failed linking relation %s to object %s",relid,objid)
                #raise
                                


    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        CmdBase.buildOptions(self)

        self.parser.add_option('-i', '--infile',
                    dest="infile", default='zendump.zip',
                    help="input file for import default is stdin")
        
        self.parser.add_option('--noindex',
                    dest='noindex',action="store_true",default=False,
                    help='Do not try to index data that was just loaded')

        self.parser.add_option('-n', '--noCommit',
                    dest='noCommit',
                    action="store_true",
                    default=0,
                    help='Do not store changes to the Dmd (for debugging)')


    def loadObjectFromXML(self, objstack=None, xmlfile=''):
        """This method can be used to load data for the root of Zenoss (default
        behavior) or it can be used to operate on a specific point in the
        Zenoss hierarchy (ZODB).

        Upon loading the XML file to be processed, the content of the XML file
        is handled (processed) by the methods in this class.
        """
        if objstack:
            self.objstack = [objstack]
        else:
            self.objstack = [self.app]
        self.links = []
        self.objectnumber = 0
        self.charvalue = ""
        zf = zipfile.ZipFile(self.options.infile, 'r', zipfile.ZIP_DEFLATED)
        tf = TemporaryFile()
        tf.write(zf.read('dump_acl_users.zexp'))
        tf.seek(0)
        self.importACLUsers(tf) 
        xtf = TemporaryFile()
        xtf.write(zf.read('dump_zenoss.xml'))
        xtf.seek(0)
        parser = make_parser()
        parser.setContentHandler(self)
        parser.parse(xtf)
        xtf.close()
        zf.close()

    def loadDatabase(self):
        """The default behavior of loadObjectFromXML() will be to use the Zope
        app object, and thus operatate on the whole of Zenoss.
        """
        self.loadObjectFromXML()

    def commit(self):
        trans = transaction.get()
        trans.note('Import from file %s using %s' 
                    % (self.options.infile, self.__class__.__name__))
        trans.commit()

    
    def importACLUsers(self, f):
        if hasattr(aq_base(self.app.zport), 'acl_users'):
            self.app.zport._delObject('acl_users')
        self.app.zport._importObjectFromFile(f, verify=0)
        #self.commit()


    def build(self):
        sitename = 'zport'
        site = getattr(self.app, sitename, None)
        if site is not None:
            raise SystemExit("zport portal object exits; exiting.")
        
        from Products.ZenModel.ZentinelPortal import manage_addZentinelPortal
        manage_addZentinelPortal(self.app, sitename)
        site = self.app._getOb(sitename)

        # build index_html
        if self.app.hasObject('index_html'):
            self.app._delObject('index_html')
        from Products.PythonScripts.PythonScript import manage_addPythonScript
        manage_addPythonScript(self.app, 'index_html')
        newIndexHtml = self.app._getOb('index_html')
        text = 'container.REQUEST.RESPONSE.redirect("/zport/dmd/")\n'
        newIndexHtml.ZPythonScript_edit('', text)
        
        # build standard_error_message
        if self.app.hasObject('standard_error_message'):
            self.app._delObject('standard_error_message')
        file = open('%s/Products/ZenModel/dtml/standard_error_message.dtml' %
                        zenhome)
        try:
            text = file.read()
        finally:
            file.close()
        import OFS.DTMLMethod
        OFS.DTMLMethod.addDTMLMethod(self.app, id='standard_error_message',
                                        file=text)

        # Convert the acl_users folder at the root to a PAS folder and update
        # the login form to use the Zenoss login form
        Security.replaceACLWithPAS(self.app, deleteBackup=True)

        # build dmd
        from Products.ZenModel.DmdBuilder import DmdBuilder
        dmdBuilder = DmdBuilder(site, "", '','','','','','','') 
        dmdBuilder.build()
#        trans = transaction.get()
#        trans.note("Initial load by zen2load.py")
#        trans.commit()
#        print "Dmd loaded"

    

if __name__ == '__main__':
    im = ImportRM()
    im.build()
    im.loadDatabase()
