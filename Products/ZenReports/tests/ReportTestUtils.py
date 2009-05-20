###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from Products.ZenModel.RRDView import RRDView
from Products.ZenModel.Device import manage_createDevice

def attributeAsRRDValue( rrdView, id, **args ):
        return getattr( rrdView, id )

class replaceGetRRDValue:
    def __init__(self, newMethod):
        self._newMethod = newMethod
    
    def __call__(self, fn):
        def wrappedFunction(*args):
            oldMethod = RRDView.getRRDValue
            RRDView.getRRDValue = self._newMethod
            try:
                return fn(*args)
            finally:
                RRDView.getRRDValue = oldMethod
        return wrappedFunction

def createTestDevice( dmd, deviceId, propertyMap={}, deviceClass='/Devices/Server' ):
        dev = manage_createDevice( dmd, deviceId, deviceClass )
        for key, value in propertyMap.iteritems():
            if hasattr( dev, key ):
                setattr( dev, key, value )
        return dev

def getDeviceIdFromRecord( record ):
    return record.values['device'].id

def getComponentIdFromRecord( record ):
    return record.values['component'].id

def assertRecordIsCorrect( test, record, values ):
    for key, value in values.iteritems():
        test.assert_( key in record.values )
        test.assertEquals( value, record[key] )
