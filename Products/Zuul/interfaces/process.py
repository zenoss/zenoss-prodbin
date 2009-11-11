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

from zope.interface import Interface, Attribute


class IProcessTreeNode(Interface):
    
    id = Attribute('The ID of the node')
    text = Attribute('The text label that represents the node')
    children = Attribute("The node's children")
    leaf = Attribute('Is this node a leaf (incapable of having children)')
    serializableObject = Attribute('A python data structure that is ready to '
                                   'be passed to json.dumps')


class IProcessService(Interface):

    def getProcessTree():
        """
        Get the Processes tree.
        """
        
