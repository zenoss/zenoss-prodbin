##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Views of filesystem directories as folders.

$Id: DirectoryView.py 40138 2005-11-15 17:47:37Z jens $
"""

import re
from os import path, listdir, stat
from sys import exc_info
from sys import platform
from warnings import warn

from AccessControl import ClassSecurityInfo
from Acquisition import aq_inner, aq_parent
from Globals import DevelopmentMode
from Globals import DTMLFile
from Globals import HTMLFile
from Globals import InitializeClass
from Globals import package_home
from Globals import Persistent
from OFS.Folder import Folder
from OFS.ObjectManager import bad_id
from zLOG import LOG, ERROR

from FSMetadata import FSMetadata
from FSObject import BadFile
from permissions import AccessContentsInformation
from permissions import ManagePortal
from utils import _dtmldir
from utils import expandpath as _new_expandpath
from utils import minimalpath
from utils import normalize


def expandpath(p):
    """ utils.expandpath() wrapper for backwards compatibility.
    """
    warn('expandpath() doesn\'t belong to DirectoryView anymore and will be '
         'removed from that module in CMF 2.0. Please import expandpath from '
         'the utils module.',
         DeprecationWarning)
    return _new_expandpath(p)

__reload_module__ = 0

# Ignore filesystem artifacts
base_ignore = ('.', '..')
# Ignore version control subdirectories
ignore = ('CVS', 'SVN', '.', '..', '.svn')
# Ignore suspected backups and hidden files
ignore_re = re.compile(r'\.|(.*~$)|#')

# and special names.
def _filtered_listdir(path, ignore=ignore):
    return [ name
             for name
             in listdir(path)
             if name not in ignore and not ignore_re.match(name) ]

class _walker:
    def __init__(self, ignore=ignore):
        # make a dict for faster lookup
        self.ignore = dict([(x, None) for x in ignore])

    def __call__(self, listdir, dirname, names):
        # filter names inplace, so filtered directories don't get visited
        names[:] = [ name
                     for name
                     in names
                     if name not in self.ignore and not ignore_re.match(name) ]
        # append with stat info
        results = [ (name, stat(path.join(dirname,name))[8])
                    for name in names ]
        listdir.extend(results)

class DirectoryInformation:
    data = None
    _v_last_read = 0
    _v_last_filelist = [] # Only used on Win32

    def __init__(self, filepath, minimal_fp, ignore=ignore):
        self._filepath = filepath
        self._minimal_fp = minimal_fp
        self.ignore=base_ignore + tuple(ignore)
        if platform == 'win32':
            self._walker = _walker(self.ignore)
        subdirs = []
        for entry in _filtered_listdir(self._filepath, ignore=self.ignore):
           entry_filepath = path.join(self._filepath, entry)
           if path.isdir(entry_filepath):
               subdirs.append(entry)
        self.subdirs = tuple(subdirs)

    def getSubdirs(self):
        return self.subdirs

    def _isAllowableFilename(self, entry):
        if entry[-1:] == '~':
            return 0
        if entry[:1] in ('_', '#'):
            return 0
        return 1

    def reload(self):
        self.data = None

    def _readTypesFile(self):
        """ Read the .objects file produced by FSDump.
        """
        types = {}
        try:
            f = open( path.join(self._filepath, '.objects'), 'rt' )
        except IOError:
            pass
        else:
            lines = f.readlines()
            f.close()
            for line in lines:
                try:
                    obname, meta_type = line.split(':')
                except ValueError:
                    pass
                else:
                    types[obname.strip()] = meta_type.strip()
        return types

    if DevelopmentMode:

        def _changed(self):
            mtime=0
            filelist=[]
            try:
                mtime = stat(self._filepath)[8]
                if platform == 'win32':
                    # some Windows directories don't change mtime
                    # when a file is added to or deleted from them :-(
                    # So keep a list of files as well, and see if that
                    # changes
                    path.walk(self._filepath, self._walker, filelist)
                    filelist.sort()
            except:
                LOG('DirectoryView',
                    ERROR,
                    'Error checking for directory modification',
                    error=exc_info())

            if mtime != self._v_last_read or filelist != self._v_last_filelist:
                self._v_last_read = mtime
                self._v_last_filelist = filelist

                return 1

            return 0

    else:

        def _changed(self):
            return 0

    def getContents(self, registry):
        changed = self._changed()
        if self.data is None or changed:
            try:
                self.data, self.objects = self.prepareContents(registry,
                    register_subdirs=changed)
            except:
                LOG('DirectoryView',
                    ERROR,
                    'Error during prepareContents:',
                    error=exc_info())
                self.data = {}
                self.objects = ()

        return self.data, self.objects

    def prepareContents(self, registry, register_subdirs=0):
        # Creates objects for each file.
        data = {}
        objects = []
        types = self._readTypesFile()
        for entry in _filtered_listdir(self._filepath, ignore=self.ignore):
            if not self._isAllowableFilename(entry):
                continue
            entry_minimal_fp = '/'.join( (self._minimal_fp, entry) )
            entry_filepath = path.join(self._filepath, entry)
            if path.isdir(entry_filepath):
                # Add a subdirectory only if it was previously registered,
                # unless register_subdirs is set.
                info = registry.getDirectoryInfo(entry_minimal_fp)
                if info is None and register_subdirs:
                    # Register unknown subdirs
                    registry.registerDirectoryByPath(entry_filepath)
                    info = registry.getDirectoryInfo(entry_minimal_fp)
                if info is not None:
                    mt = types.get(entry)
                    t = None
                    if mt is not None:
                        t = registry.getTypeByMetaType(mt)
                    if t is None:
                        t = DirectoryView
                    ob = t(entry, entry_minimal_fp)
                    ob_id = ob.getId()
                    data[ob_id] = ob
                    objects.append({'id': ob_id, 'meta_type': ob.meta_type})
            else:
                pos = entry.rfind('.')
                if pos >= 0:
                    name = entry[:pos]
                    ext = path.normcase(entry[pos + 1:])
                else:
                    name = entry
                    ext = ''
                if not name or name == 'REQUEST':
                    # Not an allowable id.
                    continue
                mo = bad_id(name)
                if mo is not None and mo != -1:  # Both re and regex formats
                    # Not an allowable id.
                    continue
                t = None
                mt = types.get(entry, None)
                if mt is None:
                    mt = types.get(name, None)
                if mt is not None:
                    t = registry.getTypeByMetaType(mt)
                if t is None:
                    t = registry.getTypeByExtension(ext)

                if t is not None:
                    metadata = FSMetadata(entry_filepath)
                    metadata.read()
                    try:
                        ob = t(name, entry_minimal_fp, fullname=entry,
                               properties=metadata.getProperties())
                    except:
                        import traceback
                        typ, val, tb = exc_info()
                        try:
                            exc_lines = traceback.format_exception( typ,
                                                                    val,
                                                                    tb )
                            LOG( 'DirectoryView', ERROR,
                                 '\n'.join(exc_lines) )

                            ob = BadFile( name,
                                          entry_minimal_fp,
                                          exc_str='\r\n'.join(exc_lines),
                                          fullname=entry )
                        finally:
                            tb = None   # Avoid leaking frame!

                    # FS-based security
                    permissions = metadata.getSecurity()
                    if permissions is not None:
                        for name in permissions.keys():
                            acquire, roles = permissions[name]
                            try:
                                ob.manage_permission(name,roles,acquire)
                            except ValueError:
                                LOG('DirectoryView',
                                    ERROR,
                                    'Error setting permissions',
                                    error=exc_info())

                    # only DTML Methods and Python Scripts can have proxy roles
                    if hasattr(ob, '_proxy_roles'):
                        try:
                            ob._proxy_roles = tuple(metadata.getProxyRoles())
                        except:
                            LOG('DirectoryView',
                                ERROR,
                                'Error setting proxy role',
                                error=exc_info())

                    ob_id = ob.getId()
                    data[ob_id] = ob
                    objects.append({'id': ob_id, 'meta_type': ob.meta_type})

        return data, tuple(objects)


class DirectoryRegistry:

    def __init__(self):
        self._meta_types = {}
        self._object_types = {}
        self._directories = {}

    def registerFileExtension(self, ext, klass):
        self._object_types[ext] = klass

    def registerMetaType(self, mt, klass):
        self._meta_types[mt] = klass

    def getTypeByExtension(self, ext):
        return self._object_types.get(ext, None)

    def getTypeByMetaType(self, mt):
        return self._meta_types.get(mt, None)

    def registerDirectory(self, name, _prefix, subdirs=1, ignore=ignore):
        # This what is actually called to register a
        # file system directory to become a FSDV.
        if not isinstance(_prefix, basestring):
            _prefix = package_home(_prefix)
        filepath = path.join(_prefix, name)
        self.registerDirectoryByPath(filepath, subdirs, ignore=ignore)

    def registerDirectoryByPath(self, filepath, subdirs=1, ignore=ignore):
        # This is indirectly called during registration of
        # a directory. As you can see, minimalpath is called
        # on the supplied path at this point.
        # The idea is that the registry will only contain
        # small paths that are likely to work across platforms
        # and SOFTWARE_HOME, INSTANCE_HOME and PRODUCTS_PATH setups
        minimal_fp = minimalpath(filepath)
        info = DirectoryInformation(filepath, minimal_fp, ignore=ignore)
        self._directories[minimal_fp] = info
        if subdirs:
            for entry in info.getSubdirs():
                entry_filepath = path.join(filepath, entry)
                self.registerDirectoryByPath( entry_filepath
                                            , subdirs
                                            , ignore=ignore
                                            )

    def reloadDirectory(self, minimal_fp):
        info = self.getDirectoryInfo(minimal_fp)
        if info is not None:
            info.reload()

    def getDirectoryInfo(self, minimal_fp):
        # This is called when we need to get hold of the information
        # for a minimal path. Can return None.
        return self._directories.get(minimal_fp, None)

    def listDirectories(self):
        dirs = self._directories.keys()
        dirs.sort()
        return dirs


_dirreg = DirectoryRegistry()
registerDirectory = _dirreg.registerDirectory
registerFileExtension = _dirreg.registerFileExtension
registerMetaType = _dirreg.registerMetaType


def listFolderHierarchy(ob, path, rval, adding_meta_type=None):
    if not hasattr(ob, 'objectValues'):
        return
    values = ob.objectValues()
    for subob in ob.objectValues():
        base = getattr(subob, 'aq_base', subob)
        if getattr(base, 'isPrincipiaFolderish', 0):

            if adding_meta_type is not None and hasattr(
                base, 'filtered_meta_types'):
                # Include only if the user is allowed to
                # add the given meta type in this location.
                meta_types = subob.filtered_meta_types()
                found = 0
                for mt in meta_types:
                    if mt['name'] == adding_meta_type:
                        found = 1
                        break
                if not found:
                    continue

            if path:
                subpath = path + '/' + subob.getId()
            else:
                subpath = subob.getId()
            title = getattr(subob, 'title', None)
            if title:
                name = '%s (%s)' % (subpath, title)
            else:
                name = subpath
            rval.append((subpath, name))
            listFolderHierarchy(subob, subpath, rval, adding_meta_type)


class DirectoryView (Persistent):
    """ Directory views mount filesystem directories.
    """
    meta_type = 'Filesystem Directory View'
    _dirpath = None
    _objects = ()

    def __init__(self, id, dirpath, fullname=None):
        self.id = id
        self._dirpath = dirpath

    def __of__(self, parent):
        dirpath = self._dirpath
        info = _dirreg.getDirectoryInfo(dirpath)
        if info is None:
            # for DirectoryViews created with CMF versions before 1.5
            # this is basically the old minimalpath() code
            dirpath = normalize(dirpath)
            index = dirpath.rfind('Products')
            if index == -1:
                index = dirpath.rfind('products')
            if index != -1:
                dirpath = dirpath[index+len('products/'):]
            info = _dirreg.getDirectoryInfo(dirpath)
            if info is not None:
                # update the directory view with a corrected path
                self._dirpath = dirpath
            else:
                warn('DirectoryView %s refers to a non-existing path %s'
                     % (self.id, dirpath), UserWarning)
        if info is None:
            data = {}
            objects = ()
        else:
            data, objects = info.getContents(_dirreg)
        s = DirectoryViewSurrogate(self, data, objects)
        res = s.__of__(parent)
        return res

    def getId(self):
        return self.id

InitializeClass(DirectoryView)


class DirectoryViewSurrogate (Folder):
    """ Folderish DirectoryView.
    """

    meta_type = 'Filesystem Directory View'
    all_meta_types = ()
    _isDirectoryView = 1

#    _is_wrapperish = 1

    security = ClassSecurityInfo()

    def __init__(self, real, data, objects):
        d = self.__dict__
        d.update(data)
        d.update(real.__dict__)
        d['_real'] = real
        d['_objects'] = objects

    def __setattr__(self, name, value):
        d = self.__dict__
        d[name] = value
        setattr(d['_real'], name, value)

    def __delattr__(self, name):
        d = self.__dict__
        del d[name]
        delattr(d['_real'], name)

    security.declareProtected(ManagePortal, 'manage_propertiesForm')
    manage_propertiesForm = DTMLFile( 'dirview_properties', _dtmldir )

    security.declareProtected(ManagePortal, 'manage_properties')
    def manage_properties( self, dirpath, REQUEST=None ):
        """ Update the directory path of the DirectoryView.
        """
        self.__dict__['_real']._dirpath = dirpath
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect( '%s/manage_propertiesForm'
                                        % self.absolute_url() )

    security.declareProtected(AccessContentsInformation, 'getCustomizableObject')
    def getCustomizableObject(self):
        ob = aq_parent(aq_inner(self))
        while getattr(ob, '_isDirectoryView', 0):
            ob = aq_parent(aq_inner(ob))
        return ob

    security.declareProtected(AccessContentsInformation, 'listCustFolderPaths')
    def listCustFolderPaths(self, adding_meta_type=None):
        """ List possible customization folders as key, value pairs.
        """
        rval = []
        ob = self.getCustomizableObject()
        listFolderHierarchy(ob, '', rval, adding_meta_type)
        rval.sort()
        return rval

    security.declareProtected(AccessContentsInformation, 'getDirPath')
    def getDirPath(self):
        return self.__dict__['_real']._dirpath

    security.declarePublic('getId')
    def getId(self):
        return self.id

InitializeClass(DirectoryViewSurrogate)


manage_addDirectoryViewForm = HTMLFile('dtml/addFSDirView', globals())

def createDirectoryView(parent, minimal_fp, id=None):
    """ Add either a DirectoryView or a derivative object.
    """
    info = _dirreg.getDirectoryInfo(minimal_fp)
    if info is None:
        fixed_minimal_fp = minimal_fp.replace('\\','/')
        info = _dirreg.getDirectoryInfo(fixed_minimal_fp)
        if info is None:
            raise ValueError('Not a registered directory: %s' % minimal_fp)
        else:
            warn('createDirectoryView() expects a slash-separated path '
                 'relative to the Products path. \'%s\' will no longer work '
                 'in CMF 2.0.' % minimal_fp,
                 DeprecationWarning)
        minimal_fp = fixed_minimal_fp
    if not id:
        id = minimal_fp.split('/')[-1]
    else:
        id = str(id)
    ob = DirectoryView(id, minimal_fp)
    parent._setObject(id, ob)

def addDirectoryViews(ob, name, _prefix):
    """ Add a directory view for every subdirectory of the given directory.

    Meant to be called by filesystem-based code. Note that registerDirectory()
    still needs to be called by product initialization code to satisfy
    persistence demands.
    """
    if not isinstance(_prefix, basestring):
        _prefix = package_home(_prefix)
    filepath = path.join(_prefix, name)
    minimal_fp = minimalpath(filepath)
    info = _dirreg.getDirectoryInfo(minimal_fp)
    if info is None:
        raise ValueError('Not a registered directory: %s' % minimal_fp)
    for entry in info.getSubdirs():
        entry_minimal_fp = '/'.join( (minimal_fp, entry) )
        createDirectoryView(ob, entry_minimal_fp, entry)

def manage_addDirectoryView(self, dirpath, id=None, REQUEST=None):
    """ Add either a DirectoryView or a derivative object.
    """
    createDirectoryView(self, dirpath, id)
    if REQUEST is not None:
        return self.manage_main(self, REQUEST)

def manage_listAvailableDirectories(*args):
    """ List registered directories.
    """
    return list(_dirreg.listDirectories())
