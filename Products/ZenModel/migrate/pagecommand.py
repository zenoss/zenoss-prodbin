###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__='''pagecommand

Add settings for pageCommand to dmd
Remove settings for snpp from dmd

'''
import Migrate
import os.path
import sys

def parseconfig(options):
    """parse a config file which has key value pairs delimited by white space"""
    if not os.path.exists(options.configfile):
        print >>sys.stderr, "WARN: config file %s not found skipping" % (
                            options.configfile)
        return
    lines = open(options.configfile).readlines()
    for line in lines:
        if line.lstrip().startswith('#'): continue
        if line.strip() == '': continue
        key, value = line.split(None, 1)
        value = value.rstrip('\r\n')
        key = key.lower()
        defval = getattr(options, key, None)
        if defval: value = type(defval)(value)
        setattr(options, key, value)


class OptionsBucket:
    pass

from Products.ZenUtils.Utils import zenPath

class pagecommand(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
        options = OptionsBucket()
        options.configfile = zenPath('etc', 'zenactions.conf')
        parseconfig(options)
        if hasattr(dmd, 'snppHost'):
            del dmd.snppHost
        if hasattr(dmd, 'snppPort'):
            del dmd.snppPort
        if not hasattr(dmd, 'pageCommand'):
            dmd.pageCommand = getattr(options, 'pagecommand', '') or '$ZENHOME/bin/zensnpp localhost 444 $RECIPIENT'

pagecommand()
