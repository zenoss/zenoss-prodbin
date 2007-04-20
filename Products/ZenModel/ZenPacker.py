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
import Globals
from AccessControl import ClassSecurityInfo

class ZenPacker(object):
    security = ClassSecurityInfo()

    security.declareProtected('Manage DMD', 'addToZenPack')
    def addToZenPack(self, ids=(), organizerPaths=(), pack=None, REQUEST=None):
        "Add elements from a displayed list of objects to a ZenPack"
        from Products.ZenModel.ZenPackable import ZenPackable
        from Products.ZenModel.ZenPack import ZenPack
        ids = list(ids) + list(organizerPaths)
        message = "You must provide a valid ZenPack"
        if pack:
            pack = self.dmd.packs._getOb(pack)
            message = 'Saved to %s' % pack.id
            if ids:
                for id in ids:
                    try:
                        obj = self.findObject(id)
                    except AttributeError, ex:
                        message = str(ex)
                        break
                    obj.buildRelations()
                    pack.packables.addRelation(obj)
            else:
                if isinstance(self, ZenPackable):
                    self.buildRelations()
                    pack.packables.addRelation(self)
                else:
                    message = 'Nothing to save'
        if REQUEST:
            if isinstance(pack, ZenPack):
                REQUEST['message'] = message
            return self.callZenScreen(REQUEST)

    def findObject(self, id):
        "Ugly hack for inconsistent object structure accross Organizers"
        result = []
        try:
            result.append(self._getOb(id))
        except AttributeError:
            pass
        for name, relationship in self._relations:
            try:
                result.append(getattr(self, name)._getOb(id))
            except AttributeError:
                pass
        if len(result) == 1:
            return result[0]
        raise AttributeError('Cannot find a unique %s on %s' % (id, self.id))
