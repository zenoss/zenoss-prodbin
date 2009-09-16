###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

"""
This module provides common utilities for monitoring Windows devices.
"""

import pysamba.twisted.reactor

def addNTLMv2Option(parser):
    """
    Adds the --ntlmv2auth option to the provided command-line parser.
    @param parser: the command-line option parser to add the argument to
    @type parser: OptionParser
    """
    parser.add_option('--ntlmv2auth',
                  dest='ntlmv2auth',
                  default=False,
                  action="store_true",
                  help="Enable NTLMv2 Authentication for Windows Devices")

def setNTLMv2Auth(options):
    """
    Enables or disables NTLMv2 Authentication in the current process based
    upon the setting of the ntlmv2auth option.
    @param options: the command-line options object
    """
    flag = False
    if getattr(options, 'ntlmv2auth', False):
        flag = True
    pysamba.twisted.reactor.setNTLMv2Authentication(flag)
