###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

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
