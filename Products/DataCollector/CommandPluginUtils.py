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

"""
Utility functions for command plugins.
"""


from time import strftime

from Products.ZenUtils import Utils

from Products.DataCollector.plugins.DataMaps \
        import RelationshipMap, ObjectMap, MultiArgs


def formatDate(timeTuple):
    """
    Formats timeTuple to YYYY/MM/DD HH:MM:SS.
    
    >>> formatDate((2008, 12, 16, 13, 56, 29, 1, 351, -1))
    '2008/12/16 13:56:29'
    """
    return strftime("%Y/%m/%d %H:%M:%S", timeTuple)
    
    
def createSoftwareDict(prodKey, vendor, description, installDate):
    """
    Create a software dictionary that can be passed as the data parameter when
    constructing an ObjectMap that represents a Software entity.
    """
    return {"id": Utils.prepId(prodKey),
            "setProductKey": MultiArgs(prodKey, Utils.prepId(vendor)),
            "setDescription": description,
            "setInstallDate": formatDate(installDate)}
            
            
def createSoftwareRelationshipMap(softwareDicts):
    """
    Takes a list of software dictionaries and returns a RelationshipMap that
    represents that software collection.
    """
    kwargs = dict(compname="os", modname="Products.ZenModel.Software")
    objmaps = []
    
    for softwareDict in softwareDicts:
        objmaps.append(ObjectMap(softwareDict, **kwargs))
        
    return RelationshipMap("software", objmaps=objmaps, **kwargs)
    