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
        if pack:
            pack = self.dmd.packs._getOb(pack)
            if ids:
                for id in ids:
                    obj = self._getOb(id)
                    pack.packables.addRelation(obj)
            else:
                if isinstance(self, ZenPackable):
                    pack.packables.addRelation(self)
        if REQUEST:
            if isinstance(pack, ZenPack):
                REQUEST['message'] = 'Saved to %s' % pack.id
            return self.callZenScreen(REQUEST)

