#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################
__doc__="""__init__

Initialize the RRDTool Product

$Id: __init__.py,v 1.4 2003/11/13 22:52:42 edahl Exp $"""


__version__ = "$Revision: 1.4 $"[11:-2]
def initialize(registrar):
    # Global module assertions for Python scripts
    from RenderServer import RenderServer,addRenderServer,manage_addRenderServer
    from RRDTargetType import RRDTargetType,addRRDTargetType, \
            manage_addRRDTargetType
    from RRDView import RRDView,addRRDView,manage_addRRDView
    from RRDDataSource import RRDDataSource,addRRDDataSource, \
            manage_addRRDDataSource
    from RRDThreshold import RRDThreshold,addRRDThreshold,manage_addRRDThreshold
    from RRDRelativeThresh import RRDRelativeThresh, \
            addRRDRelativeThresh,manage_addRRDRelativeThresh

    registrar.registerClass(
        RenderServer,
        constructors = (addRenderServer, manage_addRenderServer),
        )
    registrar.registerClass(
        RRDTargetType,
        constructors = (addRRDTargetType, manage_addRRDTargetType),
        )
    registrar.registerClass(
        RRDView,
        constructors = (addRRDView, manage_addRRDView),
        )
    registrar.registerClass(
        RRDDataSource,
        constructors = (addRRDDataSource, manage_addRRDDataSource),
        #icon = 'www/Folder_icon.gif',
        )
    registrar.registerClass(
        RRDThreshold,
        constructors = (addRRDThreshold, manage_addRRDThreshold),
        )
    registrar.registerClass(
        RRDRelativeThresh,
        constructors = (addRRDRelativeThresh, manage_addRRDRelativeThresh),
        )
