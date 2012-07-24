##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os
import re
import cgitb
from cStringIO import StringIO
import Globals
from Products.ZenUtils.Utils import unused, zenPath

unused(Globals)

pattern = re.compile(r'<p> (?P<message>.* contains the description of this error.)')

def log_tb(exc_info):
    file_ = StringIO()
    hook = cgitb.Hook(display=0, logdir=zenPath('log', 'tracebacks'), file=file_, format='text')
    os.makedirs(hook.logdir)
    hook.handle(exc_info)
    output = file_.getvalue()
    match = pattern.search(output)
    return match.group('message')
