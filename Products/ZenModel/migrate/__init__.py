##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''ZenModel.migrate.__init__.py

Use __init__.py to get all the upgrade modules imported.

'''


# by virtue of being a migration script, we often import deprecated modules
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

import os
import glob
__all__ = [ os.path.basename(f)[:-3] for f in glob.glob(os.path.dirname(__file__)+"/*.py")]

