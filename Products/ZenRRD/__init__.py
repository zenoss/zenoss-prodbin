##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""__init__

Initialize the RRDTool Product

$Id: __init__.py,v 1.4 2003/11/13 22:52:42 edahl Exp $"""


__version__ = "$Revision: 1.4 $"[11:-2]
def initialize(registrar):
    # Global module assertions for Python scripts
    from RenderServer import RenderServer,addRenderServer,manage_addRenderServer

    registrar.registerClass(
        RenderServer,
        permission="Add DMD Objects",
        constructors = (addRenderServer, manage_addRenderServer),
        )
