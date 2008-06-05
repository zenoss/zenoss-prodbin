###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__='''
ZenPackPersistence
'''

ZENPACK_PERSISTENCE_CATALOG = 'zenPackPersistence'


def CreateZenPackPersistenceCatalog(dmd):
    '''
    Create the zenPackPersistence catalog if it does not exist.
    Return the catalog
    '''
    from Products.ZCatalog.ZCatalog import manage_addZCatalog
    from Products.ZenUtils.Search import makeCaseSensitiveFieldIndex
    zcat = getattr(dmd, ZENPACK_PERSISTENCE_CATALOG, None)
    if zcat is None:
        manage_addZCatalog(dmd, ZENPACK_PERSISTENCE_CATALOG,
                                ZENPACK_PERSISTENCE_CATALOG)
        zcat = dmd._getOb(ZENPACK_PERSISTENCE_CATALOG)
        cat = zcat._catalog
        cat.addIndex('getZenPackName',makeCaseSensitiveFieldIndex('getZenPackName'))
        cat.addColumn('id')
        cat.addColumn('getPrimaryId')
    return zcat


def GetCatalogedObjects(dmd, packName):
    """
    Return a list of all the objects in the zenPackPersistence catalog
    for the given zenPack name.
    If the catalog is not found, return None.
    """
    zcat = getattr(dmd, ZENPACK_PERSISTENCE_CATALOG, None)
    if zcat is None:
        result = None
    else:
        brains = zcat(dict(getZenPackName=packName))
        result = [c.getObject() for c in brains]
    return result


class ZenPackPersistence(object):
    '''
    This is a mix-in class that should be used whenever a ZenPack-supplied
    class is going to be stored persistently in the zodb.  It provides
    for a catalog to associate objects in zodb with the ZenPacks that provide
    those objects' classes.
    
    The motivation for this is that we usually need to delete all instances
    of zenpack-supplied classes when that zenpack is deleted.  This is
    because the class for those objects no longer exists and they are just
    sad, broken, unloved objects in the zodb at that point.  This is 
    undesirable.
    
    IMPORTANT: This should be the first class listed in any subclasses's
    list of parents.  Otherwise the manage_* methods of the other classes
    will likely be called and these skipped.
    '''

    # Subclasses should set this to the id of the ZenPack or they
    # should override getZenPackName()
    # ZENPACKID = 'ZenPacks.my.name'

    def getZenPackName(self):
        '''
        '''
        if not self.ZENPACKID:
            from ZenPack import ZenPackException
            raise ZenPackException('The class %s must define ZENPACKID ' %
                    str(self.__class__) +
                    'or override getZenPackName().')
        # Should we check to make sure ZENPACKID matches the name of an
        # installed ZenPack?
        return self.ZENPACKID


    def getZenPack(self, context):
        """
        Return the ZenPack instance that provides this object.
        """
        return context.dmd.ZenPackManager.packs._getOb(
                                            self.getZenPackName(), None)
    
    
    def path(self, *parts):
        """
        Return the path to the installed ZenPack directory or a subdirectory.
        Example: zenpack.path('libexec') would return something like
        $ZENHOME/ZenPacks/ZenPacks.Me.MyZenPack/ZenPacks/Me/MyZenPack/libexec
        """
        zp = self.getZenPack(self)
        return zp.path(*parts)


    # index_object and unindex_object are overridden so that instances
    # can participate in other catalogs, not just the 
    # ZENPACK_PERSISTENCE_CATALOG.
    # If we used the standard method of just setting default_catalog in
    # this class then ZenPacks would not be able to override Zenoss
    # classes that already participate in catalogs, eg DeviceClass.
    
    def index_object(self):
        """A common method to allow Findables to index themselves."""
        cat = getattr(self, ZENPACK_PERSISTENCE_CATALOG, None)
        if cat is not None:
            cat.catalog_object(self, self.getPrimaryId())            
        super(ZenPackPersistence, self).index_object()


    def unindex_object(self):
        """A common method to allow Findables to unindex themselves."""
        cat = getattr(self, ZENPACK_PERSISTENCE_CATALOG, None)
        if cat is not None:
            cat.uncatalog_object(self.getPrimaryId())
        super(ZenPackPersistence, self).unindex_object()


    # manage_afterAdd, manage_afterClose and manage_beforeDelete
    # are the magic methods that make the indexing happen

    def manage_afterAdd(self, item, container):
        """
        """
        self.index_object()
        super(ZenPackPersistence,self).manage_afterAdd(item, container)


    def manage_afterClone(self, item):
        """
        """
        super(ZenPackPersistence,self).manage_afterClone(item)
        self.index_object()


    def manage_beforeDelete(self, item, container):
        """
        """
        super(ZenPackPersistence,self).manage_beforeDelete(item, container)
        self.unindex_object()
