#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''ZenModel.migrate.__init__.py

Use __init__.py to get all the upgrade modules imported.

$Id$
'''

__version__ = "$Revision$"[11:-2]

import evtprops
import kill_cricket
import reindex_history
import hoist_perf_data
import interfacename_convert
