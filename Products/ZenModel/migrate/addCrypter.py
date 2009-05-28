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

"""
Add dmd.crypter a do-nothing encryption service.
"""

import Migrate
from Products.ZenModel.Crypter import Crypter

class addCrypter(Migrate.Step):
    version = Migrate.Version(2, 5, 0)
    
    def cutover(self, dmd):
        crypterId = 'Encryption'
        if crypterId not in dmd.objectIds():
            crypter = Crypter(crypterId)
            crypter.isInTree = False
            dmd._setObject(crypterId, crypter)
            
addCrypter()
