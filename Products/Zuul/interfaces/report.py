###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.interface import Attribute
from Products.Zuul.interfaces import IFacade
from tree import ITreeNode

class IReportFacade(IFacade):
    pass

class IReportClassNode(ITreeNode):
    deletable = Attribute("can this node be deleted?")
    edit_url = Attribute("where can this node be edited?")

class IReportNode(ITreeNode):
    deletable = Attribute("can this node be deleted?")
    edit_url = Attribute("where can this node be edited?")

