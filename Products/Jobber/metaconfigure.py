##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from celery.registry import tasks
from celery.app import current_app

def job(_context, class_, name=None):
    if name is not None:
        class_.name = name
    tasks.register(class_)
