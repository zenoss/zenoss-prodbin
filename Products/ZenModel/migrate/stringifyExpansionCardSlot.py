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

import Migrate

import logging
log = logging.getLogger('zen.migrate')


class StringifyExpansionCardSlot(Migrate.Step):
    version = Migrate.Version(2, 5, 1)

    def cutover(self, dmd):
        try:
            for brain in dmd.Devices.componentSearch(meta_type='ExpansionCard'):
                card = brain.getObject()
                if isinstance(card.slot, int):
                    card.slot = str(card.slot)
        except Exception, ex:
            log.error('Error converting expansion card slots to strings: %s',
                ex)


StringifyExpansionCardSlot()
