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

__doc__='''smtpsnpp

Add settings for smtp/snpp host/port to dmd

'''
import Migrate
import os.path

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

class smtpsnpp(Migrate.Step):
    version = Migrate.Version(1, 0, 0)

    def cutover(self, dmd):
        options = OptionsBucket()
        options.configfile = os.path.join(
                            os.environ['ZENHOME'], 'etc', 'zenactions.conf')
        parseconfig(options)
        if not hasattr(dmd, 'smtpHost'):
            dmd.smtpHost = getattr(options, 'smtphost', '') or 'localhost'
        if not hasattr(dmd, 'smtpPort'):
            try:
                dmd.smtpPort = int(getattr(options, 'smtpport', ''))
            except ValueError:
                dmd.smtpPort = 25
        if not hasattr(dmd, 'snppHost'):
            dmd.snppHost = getattr(options, 'snpphost', '') or 'localhost'
        if not hasattr(dmd, 'snppPort'):
            try:
                dmd.snppPort = int(getattr(options, 'snppport', ''))
            except ValueError:
                dmd.snppPort = 444

smtpsnpp()
