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
from Products.ZenRelations.ToOneRelationship import ToOneRelationship


def cleanUpRelationships(ob, event):
    """
    Unlinks non-container relationships when their targets are being deleted.
    """
    if getattr(event.object, "_operation", -1) < 1:
        # Don't bother in the case where the other side is a container.
        if not (isinstance(ob, ToOneRelationship) and
            ob.remoteTypeName() == 'ToManyCont'):
            ob._remoteRemove()


def resetUnderscoreOperation(ob, event):
    """
    Make sure that the _operation attribute on a RelationshipManager is reset
    after paste/move/rename.
    """
    if ob._operation > -1: ob._operation = -1
