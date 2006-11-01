#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''smtpsnpp

Add settings for smtp/snpp host/port to dmd

'''
import Migrate
import Products.ZenUtils.Utils as Utils
import os.path

class OptionsBucket:
    pass

class smtpsnpp(Migrate.Step):
    version = Migrate.Version(1, 0, 0)

    def cutover(self, dmd):
        options = OptionsBucket()
        options.configfile = os.path.join(
                            os.environ['ZENHOME'], 'etc', 'zenactions.conf')
        Utils.parseconfig(options)
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
