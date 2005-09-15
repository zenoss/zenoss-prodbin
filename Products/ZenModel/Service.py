#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""Service.py

Service is a function provided by computer (like a server).  it
is defined by a protocol type (udp/tcp) and a port number.

$Id: Service.py,v 1.15 2003/03/11 23:32:13 edahl Exp $"""

__version__ = "$Revision: 1.15 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass

from Instance import Instance

class Service(Instance):
    portal_type = meta_type = 'Service'
    manage_options = Instance.manage_options
