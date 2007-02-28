#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################
__doc__="""__init__

Initialize the RRDTool Product

$Id: __init__.py,v 1.4 2003/11/13 22:52:42 edahl Exp $"""


__version__ = "$Revision: 1.4 $"[11:-2]
def initialize(registrar):
    # Global module assertions for Python scripts
    from RenderServer import RenderServer,addRenderServer,manage_addRenderServer
    from ProxyRenderServer import ProxyRenderServer,addProxyRenderServer,manage_addProxyRenderServer

    registrar.registerClass(
        RenderServer,
        permission="Add DMD Objects",
        constructors = (addRenderServer, manage_addRenderServer),
        )
    registrar.registerClass(
        ProxyRenderServer,
        permission="Add DMD Objects",
        constructors = (addProxyRenderServer, manage_addProxyRenderServer),
        )