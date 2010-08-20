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
import Migrate
from Products.ZenUtils.orm.meta import Base
from Products.ZenUtils.orm import init_model

class CreateORMTables(Migrate.Step):
    version = Migrate.Version(3, 1, 0)

    def cutover(self, dmd):
        from Products.ZenChain.guids import Guid
        from Products.ZenChain.impacts import ImpactRelationship
        # Create tables imported above
        zem = dmd.ZenEventManager
        init_model(
            host=zem.host,
            db=zem.database,
            port=zem.port,
            user=zem.username,
            passwd=zem.password
        )
        try:
            Base.metadata.create_all()
        except Exception, e:
            pass
        else:
            if getattr(dmd, 'guid_table', None) is not None:
                del dmd.guid_table


createORMTables = CreateORMTables()
