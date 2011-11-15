###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

class NmapExecutionError(Exception):
    """
    NmapExecutionError raised when there was a problem calling nmap.
    """

    def __init__(self, msg=None, exitCode=None, stdout=None, stderr=None, args=None):
        if msg is None:
            msg = "NmapExecution Error : %r, %r, %r" % (exitCode, stdout, stderr)
        super(NmapExecutionError, self).__init__(msg)
        self.exitCode = exitCode
        self.stdout = stdout
        self.stderr = stderr
        self.args = args
        
from lxml import etree as _etree

class NmapParsingError(_etree.XMLSyntaxError):
    """
    NmapParsingError is raise when there is an error parsing the nmap XML output.
    """
    pass


class NmapNotFound(Exception):
    """
    NmapNotFound raised when nmap is not found.
    """
    pass

class NmapNotSuid(Exception):
    """
    NmapNotFound raised when nmap is not found.
    """
    pass
