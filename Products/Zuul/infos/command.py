###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.Zuul.facades import InfoBase

class UserCommandInfo(InfoBase):

    def getCommand(self):
        return self._object.command

    def setCommand(self, command):
        self._object.command = command

    command = property(getCommand, setCommand)
