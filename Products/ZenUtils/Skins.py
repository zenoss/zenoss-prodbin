import sys, os

def registerSkin(self, base, positionAfter='custom'):
    """setup the skins in a product"""
    layers = []
    for p, ds, fs in os.walk(os.path.join(base, 'skins')):
        for d in ds:
            if not d.startswith('.'):
                layers.append(d)
        break
    try:
        import string 
        from Products.CMFCore.utils import getToolByName
        from Products.CMFCore.DirectoryView import addDirectoryViews
        skinstool = getToolByName(self, 'portal_skins')
        for layer in layers:
            if layer not in skinstool.objectIds():
                addDirectoryViews(skinstool, 'skins', base)
        skins = skinstool.getSkinSelections()
        for skin in skins:
            path = skinstool.getSkinPath(skin)
            path = map(string.strip, string.split(path,','))
            for layer in layers:
                if layer not in path:
                    try:
                        path.insert(path.index(positionAfter)+1, layer)
                    except ValueError:
                        path.append(layer)
            path = ','.join(path)
            skinstool.addSkinSelection(skin, path)
    except ImportError, e:
        if "Products.CMFCore.utils" in e.args: pass
        else: raise
    except AttributeError, e:
        if "portal_skin" in e.args: pass
        else: raise
