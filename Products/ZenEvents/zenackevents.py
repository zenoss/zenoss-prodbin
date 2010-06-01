#!/usr/bin/env python
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import Globals

from Products.ZenUtils.ZenScriptBase import ZenScriptBase

class zenackevents(ZenScriptBase):
    
    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZenScriptBase.buildOptions(self)
        self.parser.add_option('--userid',
                    dest="userid",default="",
                    help="name of user who is acking the event")
        
        self.parser.add_option('--evid',
                    dest="evids", action="append",
                    help="event id that is acked")

        self.parser.add_option('--state', type='int',
                    dest="state", default=1,
                    help="event id that is acked [default: ack]")

    def ack(self):
        self.dmd.ZenEventManager.manage_setEventStates(self.options.state,
                                    self.options.evids,self.options.userid)


if __name__ == '__main__':
    zae = zenackevents(connect=True)
    zae.ack()
