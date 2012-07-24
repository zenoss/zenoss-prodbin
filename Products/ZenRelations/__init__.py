##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""__init__

Initialize the RelationshipManager Product

$Id: __init__.py,v 1.9 2002/12/06 14:25:57 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

import logging
from RelationshipManager import RelationshipManager, addRelationshipManager, \
                                manage_addRelationshipManager
from ToOneRelationship import ToOneRelationship, addToOneRelationship, \
                                manage_addToOneRelationship
from ToManyRelationship import ToManyRelationship, addToManyRelationship, \
                                manage_addToManyRelationship
from ToManyContRelationship import ToManyContRelationship, \
                                addToManyContRelationship, \
                                manage_addToManyContRelationship
from Products.ZenRelations.ZenPropertyManager import setDescriptors

log = logging.getLogger("zen.ZenRelations")

class ZODBConnectionError(Exception):
    pass

def initialize(registrar):
    registrar.registerClass(
        RelationshipManager,
        constructors = (addRelationshipManager, manage_addRelationshipManager))
    registrar.registerBaseClass(RelationshipManager)
    registrar.registerClass(
        ToOneRelationship,
        constructors = (addToOneRelationship, manage_addToOneRelationship),
        icon = 'www/ToOneRelationship_icon.gif')
    registrar.registerClass(
        ToManyRelationship,
        constructors = (addToManyRelationship, manage_addToManyRelationship),
        icon = 'www/ToManyRelationship_icon.gif')
    registrar.registerClass(
        ToManyContRelationship,
        constructors = (addToManyContRelationship, 
                        manage_addToManyContRelationship),
        icon = 'www/ToManyContRelationship_icon.gif')

def registerDescriptors(event):
    """
    Handler for IZopeApplicationOpenedEvent which registers property descriptors.
    """
    zport = getattr(event.app, 'zport', None)
    # zport may not exist if we are using zenbuild to initialize the database
    if zport:
        try:
            setDescriptors(zport.dmd)
        except Exception, e:
            args = (e.__class__.__name__, e)
            log.info("Unable to set property descriptors: %s: %s", *args)
