###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

"""
Do nothing implemenation of a class that provides encrypt and decrypt methods.
"""

from OFS.SimpleItem import SimpleItem

import logging
log = logging.getLogger("zen.Crypter")

class Crypter(SimpleItem):
    
    def encrypt(self, plainText):
        "simply returns the plainText parameter"
        log.debug("Not encrypting %s", plainText)
        return plainText
        
    def decrypt(self, encryptedText):
        "simply returns the encryptedText parameter"
        log.debug("Not decrypting %s", encryptedText)
        return encryptedText
