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

__doc__="""Util

Utility functions for the Confmon Product

$Id: IpUtil.py,v 1.4 2002/12/18 18:50:47 edahl Exp $"""

__version__ = "$Revision: 1.4 $"[11:-2]

import types
import re
import string

from Products.ZenUtils.Exceptions import ZentinelException

class IpAddressError(ZentinelException): pass


isip = re.compile("^\d+\.\d+\.\d+\.\d+$").search
"""return match if this is an ip."""


def checkip(ip):
    """check that an ip is valid"""
    if ip == '': return 1
    try:
        octs = ip.split('.')
    except:
        raise IpAddressError, '%s is not a dot delimited address' % ip
    retval = 1
    #if len(octs) != 4 or int(octs[0]) == 0: 
    if len(octs) != 4:
        retval = 0
    else:
        for o in octs:
            try:
                if not (0 <= int(o) <= 255):
                    retval = 0
            except:
                retval = 0
    if not retval:
        raise IpAddressError, "%s is an invalid address" % ip
    return retval


def numbip(ip):
    """convert a string ip to number"""
    checkip(ip)
    octs = ip.split('.')
    octs.reverse()
    i = 0L
    for j in range(len(octs)):
        i += (256l ** j) * int(octs[j])
    return i    

_masks = (
    0x000000ffL,
    0x0000ff00L,
    0x00ff0000L,
    0xff000000L,
    )


def ipFromIpMask(ipmask):
    """get just the ip from an ip mask pair like 1.1.1.1/24"""
    return ipmask.split("/")[0]


def strip(ip):
    """convert a number ip to a string"""
    o = []
    for i in range(len(_masks)):
        t = ip & _masks[i]
        o.append(str(t >> (i*8)))
    o.reverse()
    return '.'.join(o)


def hexToBits(hex):
    """convert hex number (0xff000000 of netbits to numeric netmask (8)"""
    return maskToBits(hexToMask(hex))
    

def hexToMask(hex):
    '''converts a netmask represented in hex to octets represented in
    decimal.  e.g. "0xffffff00" -> "255.255.255.0"'''
    
    if hex.find('x') < 0:
        return "255.255.255.255"
    
    hex = list(hex.lower().split('x')[1])
    octets = []
    while len(hex) > 0:
        snippit = list(hex.pop() + hex.pop())
        snippit.reverse()
        decimal = int(string.join(snippit, ''), 16)
        octets.append(str(decimal))

    octets.reverse()
    return string.join(octets, '.')


def maskToBits(netmask):
    """convert string rep of netmask to number of bits"""
    if type(netmask) == types.StringType and netmask.find('.') > -1: 
        test = 0xffffffffL
        if netmask[0]=='0': return 0
        masknumb = numbip(netmask)
        for i in range(32):
            if test == masknumb: return 32-i
            test = test - 2 ** i
        return None
    else:
        return int(netmask)
       

def bitsToMaskNumb(netbits):
    """convert integer number of netbits to string netmask"""
    masknumb = 0L
    netbits=int(netbits)
    for i in range(32-netbits, 32):
        masknumb += 2L ** i
    return masknumb
   

def bitsToMask(netbits):
    return strip(bitsToMaskNumb(netbits))


def getnet(ip, netmask):
    """get network address of ip as string netmask is in form 255.255.255.0"""
    checkip(ip)
    ip = numbip(ip)
    if 0 < int(netmask) <= 32:
        netmask = bitsToMaskNumb(netmask)
    else:
        checkip(netmask)
        netmask = numbip(netmask)
    return ip & netmask


def getnetstr(ip, netmask):
    """return network number as string"""
    return strip(getnet(ip, netmask))

