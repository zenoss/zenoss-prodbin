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

from zope.interface import Interface

class IReturnPayloadProcessor(Interface):
    """
    Implementers process returned data from callhome
    """

    def process(dmd, data):
        """
        Process returned Callhome data. These must be named adapters, and the name
        of the adapter should correspond to the its key in the callhome return
        payload.
        
        @param dmd: Reference to dmd
        @param data: Callhome return payload
        @return: None
        """
