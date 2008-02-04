######################################################################
#
# Copyright 2007 Zenoss, Inc.  All Rights Reserved.
#
######################################################################

__doc__="ZenPack Template"

__import__('pkg_resources').declare_namespace(__name__)

import Globals
import os.path

skinsDir = os.path.join(os.path.dirname(__file__), 'skins')
from Products.CMFCore.DirectoryView import registerDirectory
registerDirectory(skinsDir, globals())
