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
import Migrate
import logging
log = logging.getLogger('zen.migrate')

class AddressEncoding(Migrate.Step):
    version = Migrate.Version(2, 6, 0)

    def cutover(self, dmd):
        for loc in dmd.Locations.getSubOrganizers():
            try:
                loc.address.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    loc.address = loc.address.decode('latin-1').encode('utf-8')
                except:
                    log.error("Unable to decode address '%s'" % loc.address + \
                              " on location %s" % loc.id)
        dmd.geocache = ''

AddressEncoding()
