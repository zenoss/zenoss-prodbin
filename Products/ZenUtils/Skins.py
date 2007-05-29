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
import sys, os
import string 


def skinDirs(base):
    layers = []
    for p, ds, fs in os.walk(os.path.join(base, 'skins')):
        for d in ds:
            if not d.startswith('.'):
                layers.append(d)
        # stop at one level
        return layers
    

def registerSkin(self, base, positionAfter='custom'):
    """setup the skins in a product"""
    layers = skinDirs(base)
    try:
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

def unregisterSkin(self, base, positionAfter='custom'):
    """setup the skins in a product"""
    layers = skinDirs(base)
    try:
        from Products.CMFCore.utils import getToolByName
        skinstool = getToolByName(self, 'portal_skins')
        for layer in layers:
            if layer in skinstool.objectIds():
                try:
                    skinstool._delOb(layer)
                except AttributeError:
                    pass
        obs = skinstool._objects
        goodlayers = filter(lambda x:getattr(skinstool, x['id'], False), obs)
        skinstool._objects = tuple(goodlayers)
    except ImportError, e:
        if "Products.CMFCore.utils" in e.args: pass
        else: raise
    except AttributeError, e:
        if "portal_skin" in e.args: pass
        else: raise

