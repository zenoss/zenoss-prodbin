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

__doc__="""BasicDataSource

Defines attributes for how a datasource will be graphed
and builds the nessesary DEF and CDEF statements for it.
"""

import Products.ZenModel.RRDDataSource as RRDDataSource
from AccessControl import ClassSecurityInfo, Permissions
from Globals import InitializeClass
from Products.ZenEvents.ZenEventClasses import Cmd_Fail


#def manage_addRRDDataSource(context, id, dsClassName, dsType, REQUEST = None):
#    """make a RRDDataSource"""
#    raise '####### HEY #####'
#    for dsClass in 
#    ds = RRDDataSource(id)
#    context._setObject(ds.id, ds)
#    if REQUEST is not None:
#        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

#addRRDDataSource = DTMLFile('dtml/addRRDDataSource',globals())


def checkOid(oid):
    import string
    for c in string.whitespace:
        oid = oid.replace(c, '')
    oid = oid.strip('.')
    numbers = oid.split('.')
    map(int, numbers)
    if len(numbers) < 3:
        raise ValueError("OID too short")
    return oid



#class RRDDataSourceError(Exception): pass


class BasicDataSource(RRDDataSource.RRDDataSource):

    sourcetypes = ('SNMP', 'XMLRPC', 'COMMAND')
    
    sourcetype = 'SNMP'
    oid = ''
    xmlrpcURL = ''
    xmlrpcUsername = ''
    xmlrpcPassword = ''
    xmlrpcMethodName = ''
    # [[param1, int], [param2, string], ...]
    xmlrpcMethodParameters = []

    usessh = False

    _properties = RRDDataSource.RRDDataSource._properties + (
        {'id':'oid', 'type':'string', 'mode':'w'},
        {'id':'xmlrpcURL', 'type':'string', 'mode':'w'},
        {'id':'xmlrpcUsername', 'type':'string', 'mode':'w'},
        {'id':'xmlrpcPassword', 'type':'string', 'mode':'w'},
        {'id':'xmlrpcMethodName', 'type':'string', 'mode':'w'},
        {'id':'xmlrpcMethodParameters', 'type':'lines', 'mode':'w'},
        {'id':'usessh', 'type':'boolean', 'mode':'w'},
        )

    _relations = RRDDataSource.RRDDataSource._relations + (
        )
    
    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
    { 
        'immediate_view' : 'editBasicDataSource',
        'actions'        :
        ( 
            { 'id'            : 'edit'
            , 'name'          : 'Data Source'
            , 'action'        : 'editBasicDataSource'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )

    security = ClassSecurityInfo()


    def getDescription(self):
        if self.sourcetype == "SNMP":
            return self.oid
        if self.sourcetype == "XMLRPC":
            return self.xmlrpcURL+" ("+self.xmlrpcMethodName+")"
        if self.sourcetype == "COMMAND":
            if self.usessh:
                return self.commandTemplate + " over SSH"
            else:
                return self.commandTemplate
        return RRDDataSource.RRDDataSource.getDescription(self)


    def useZenCommand(self):
        if self.sourceType == 'COMMAND':
            return True
        return False


    def getXmlRpcMethodParameters(self):
        """Return the list of all parameters as a list.
           ["param1 (type)", "param2 (type)", ...]
        """
        params = []
        for param in self.xmlrpcMethodParameters: 
            p = "%s (%s)" % (param[0], param[1])
            params.append(p)
        return params


    def zmanage_editProperties(self, REQUEST=None):
        'add some validation'
        if REQUEST:
            oid = REQUEST.get('oid', '')
            if oid:
                try: 
                    REQUEST.form['oid'] = checkOid(oid)
                except ValueError:
                    REQUEST['message'] = "%s is an invalid OID" % oid 
                    return self.callZenScreen(REQUEST)
                    
            if REQUEST.get('sourcetype') == 'COMMAND':
                if REQUEST.form.get('eventClass', '/') == '/':
                    REQUEST.form['eventClass'] = Cmd_Fail
        return RRDDataSource.RRDDataSource.zmanage_editProperties(
                                                                self, REQUEST)

InitializeClass(BasicDataSource)
