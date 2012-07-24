##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from celery.app import App

class ZenossCelery(App):
    def __init__(self, *args, **kwargs):
        App.__init__(self, *args, **kwargs)
