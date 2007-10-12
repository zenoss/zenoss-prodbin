###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information plaease visit: http://www.zenoss.com/oss/
#
###########################################################################
import Migrate

import Globals

import logging
log = logging.getLogger("zen.migrate")

class DeleteADPNewProductClass(Migrate.Step):
    version = Migrate.Version(2, 1, 0)
    
    def cutover(self, dmd):  
        try:
            adp = dmd.getObjByPath('/zport/dmd/Manufacturers/ADP')
            adp.manage_deleteProducts(ids=['new'])
        except KeyError:
            log.info('Could not find the manufacturer ADP')
        except AttributeError:
            log.info('Could not the product new on manufacturer ADP')
        except:
            log.error('Unknown error occurred')
            
DeleteADPNewProductClass()
