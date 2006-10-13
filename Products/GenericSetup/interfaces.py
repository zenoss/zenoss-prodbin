##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" GenericSetup product interfaces

$Id: interfaces.py 70268 2006-09-20 21:07:49Z tseaver $
"""

from zope.interface import Interface
from zope.schema import Text
from zope.schema import TextLine

# Please note that these values may change. Always import 
# the values from here instead of using the values directly.
BASE, EXTENSION = 1, 2
SKIPPED_FILES = ('CVS', '.svn', '_svn', '_darcs')
SKIPPED_SUFFIXES = ('~',)


class IPseudoInterface( Interface ):

    """ API documentation;  not testable / enforceable.
    """


class ISetupEnviron(Interface):

    """Context for im- and export adapters.
    """

    def getLogger(name):
        """Get a logger with the specified name, creating it if necessary.
        """

    def shouldPurge():
        """When installing, should the existing setup be purged?
        """


class ISetupContext(ISetupEnviron):

    """ Context used for export / import plugins.
    """
    def getSite():

        """ Return the site object being configured / dumped.
        """

    def getSetupTool():

        """ Return the site object being configured / dumped.
        """

    def getEncoding():

        """ Get the encoding used for configuration data within the site.

        o Return None if the data should not be encoded.
        """

    def listNotes():
        """ Return notes recorded by this context.
        
        o Result a sequence of (component, message) tuples
        """

    def clearNotes():
        """ Clear all notes recorded by this context.
        """

class IImportContext( ISetupContext ):

    def readDataFile( filename, subdir=None ):

        """ Search the current configuration for the requested file.

        o 'filename' is the name (without path elements) of the file.

        o 'subdir' is an optional subdirectory;  if not supplied, search
          only the "root" directory.

        o Return the file contents as a string, or None if the
          file cannot be found.
        """

    def getLastModified( path ):

        """ Return the modification timestamp of the item at 'path'.

        o Result will be a DateTime instance.

        o Search profiles in the configuration in order.

        o If the context is filesystem based, return the 'stat' timestamp
          of the file / directory to which 'path' points.

        o If the context is ZODB-based, return the Zope modification time
          of the object to which 'path' points.

        o Return None if 'path' does not point to any object.
        """

    def isDirectory( path ):

        """ Test whether path points to a directory / folder.

        o If the context is filesystem based, check that 'path' points to
          a subdirectory within the "root" directory.

        o If the context is ZODB-based, check that 'path' points to a
          "container" under the context's tool.

        o Return None if 'path' does not resolve;  otherwise, return a
          bool.
        """

    def listDirectory( path, skip=SKIPPED_FILES ):

        """ List IDs of the contents of a  directory / folder.

        o Omit names in 'skip'.

        o If 'path' does not point to a directory / folder, return None.
        """


class IImportPlugin( IPseudoInterface ):

    """ Signature for callables used to import portions of site configuration.
    """
    def __call__( context ):

        """ Perform the setup step.

        o Return a message describing the work done.

        o 'context' must implement IImportContext.
        """

class IExportContext( ISetupContext ):

    def writeDataFile( filename, text, content_type, subdir=None ):

        """ Write data into the specified location.

        o 'filename' is the unqualified name of the file.

        o 'text' is the content of the file.

        o 'content_type' is the MIMEtype of the file.

        o 'subdir', if passed, is a path to a subdirectory / folder in
          which to write the file;  if not passed, write the file to the
          "root" of the target.
        """

class IExportPlugin( IPseudoInterface ):

    """ Signature for callables used to export portions of site configuration.
    """
    def __call__( context ):

        """ Write export data for the site wrapped by context.

        o Return a message describing the work done.

        o 'context' must implement IExportContext.  The plugin will use
          its 'writeDataFile' method for each file to be exported.
        """

class IStepRegistry( Interface ):

    """ Base interface for step registries.
    """
    def listSteps():

        """ Return a sequence of IDs of registered steps.

        o Order is not significant.
        """

    def listStepMetadata():

        """ Return a sequence of mappings describing registered steps.

        o Mappings will be ordered alphabetically.
        """

    def getStepMetadata( key, default=None ):

        """ Return a mapping of metadata for the step identified by 'key'.

        o Return 'default' if no such step is registered.

        o The 'handler' metadata is available via 'getStep'.
        """

    def generateXML():

        """ Return a round-trippable XML representation of the registry.

        o 'handler' values are serialized using their dotted names.
        """

    def parseXML( text ):

        """ Parse 'text'.
        """

class IImportStepRegistry( IStepRegistry ):

    """ API for import step registry.
    """
    def sortSteps():

        """ Return a sequence of registered step IDs

        o Sequence is sorted topologically by dependency, with the dependent
          steps *after* the steps they depend on.
        """

    def checkComplete():

        """ Return a sequence of ( node, edge ) tuples for unsatisifed deps.
        """

    def getStep( key, default=None ):

        """ Return the IImportPlugin registered for 'key'.

        o Return 'default' if no such step is registered.
        """

    def registerStep( id
                    , version
                    , handler
                    , dependencies=()
                    , title=None
                    , description=None
                    ):
        """ Register a setup step.

        o 'id' is a unique name for this step,

        o 'version' is a string for comparing versions, it is preferred to
          be a yyyy/mm/dd-ii formatted string (date plus two-digit
          ordinal).  when comparing two version strings, the version with
          the lower sort order is considered the older version.

          - Newer versions of a step supplant older ones.

          - Attempting to register an older one after a newer one results
            in a KeyError.

        o 'handler' should implement IImportPlugin.

        o 'dependencies' is a tuple of step ids which have to run before
          this step in order to be able to run at all. Registration of
          steps that have unmet dependencies are deferred until the
          dependencies have been registered.

        o 'title' is a one-line UI description for this step.
          If None, the first line of the documentation string of the handler
          is used, or the id if no docstring can be found.

        o 'description' is a one-line UI description for this step.
          If None, the remaining line of the documentation string of
          the handler is used, or default to ''.
        """

class IExportStepRegistry( IStepRegistry ):

    """ API for export step registry.
    """
    def getStep( key, default=None ):

        """ Return the IExportPlugin registered for 'key'.

        o Return 'default' if no such step is registered.
        """

    def registerStep( id, handler, title=None, description=None ):

        """ Register an export step.

        o 'id' is the unique identifier for this step

        o 'handler' should implement IExportPlugin.

        o 'title' is a one-line UI description for this step.
          If None, the first line of the documentation string of the step
          is used, or the id if no docstring can be found.

        o 'description' is a one-line UI description for this step.
          If None, the remaining line of the documentation string of
          the step is used, or default to ''.
        """

class IToolsetRegistry( Interface ):

    """ API for toolset registry.
    """
    def listForbiddenTools():

        """ Return a list of IDs of tools which must be removed, if present.
        """

    def addForbiddenTool(tool_id ):

        """ Add 'tool_id' to the list of forbidden tools.

        o Raise KeyError if 'tool_id' is already in the list.

        o Raise ValueError if 'tool_id' is in the "required" list.
        """

    def listRequiredTools():

        """ Return a list of IDs of tools which must be present.
        """

    def getRequiredToolInfo( tool_id ):

        """ Return a mapping describing a partiuclar required tool.

        o Keys include:

          'id' -- the ID of the tool

          'class' -- a dotted path to its class

        o Raise KeyError if 'tool_id' id not a known tool.
        """

    def listRequiredToolInfo():

        """ Return a list of IDs of tools which must be present.
        """

    def addRequiredTool( tool_id, dotted_name ):

        """ Add a tool to our "required" list.

        o 'tool_id' is the tool's ID.

        o 'dotted_name' is a dotted (importable) name of the tool's class.

        o Raise KeyError if we have already registered a class for 'tool_id'.

        o Raise ValueError if 'tool_id' is in the "forbidden" list.
        """

class IProfileRegistry( Interface ):

    """ API for profile registry.
    """
    def getProfileInfo( profile_id, for_=None ):

        """ Return a mapping describing a registered filesystem profile.

        o Keys include:

          'id' -- the ID of the profile

          'title' -- its title

          'description' -- a textual description of the profile

          'path' -- a path to the profile on the filesystem.

          'product' -- the name of the product to which 'path' is
             relative (None for absolute paths).

          'type' -- either BASE or EXTENSION
        
        o 'for_', if passed, should be the interface specifying the "site
            type" for which the profile is relevant, e.g.
            Products.CMFCore.interfaces.ISiteRoot or
            Products.PluggableAuthService.interfaces.IPluggableAuthService.
            If 'None', list all profiles.
        """

    def listProfiles( for_=None ):

        """ Return a list of IDs for registered profiles.
        
        o 'for_', if passed, should be the interface specifying the "site
            type" for which the profile is relevant, e.g.
            Products.CMFCore.interfaces.ISiteRoot or
            Products.PluggableAuthService.interfaces.IPluggableAuthService.
            If 'None', list all profiles.
        """

    def listProfileInfo( for_=None ):

        """ Return a list of mappings describing registered profiles.

        o See 'getProfileInfo' for a description of the mappings' keys.
        
        o 'for_', if passed, should be the interface specifying the "site
            type" for which the profile is relevant, e.g.
            Products.CMFCore.interfaces.ISiteRoot or
            Products.PluggableAuthService.interfaces.IPluggableAuthService.
            If 'None', list all profiles.
        """

    def registerProfile( name
                       , title
                       , description
                       , path
                       , product=None
                       , profile_type=BASE
                       , for_=None
                       ):
        """ Add a new profile to the registry.

        o If an existing profile is already registered for 'product:name',
          raise KeyError.

        o If 'product' is passed, then 'path' should be interpreted as
          relative to the corresponding product directory.
        
        o 'for_', if passed, should be the interface specifying the "site
          type" for which the profile is relevant, e.g.
          Products.CMFCore.interfaces.ISiteRoot or
          Products.PluggableAuthService.interfaces.IPluggableAuthService.
          If 'None', the profile might be used in any site.
        """

class ISetupTool( Interface ):

    """ API for SetupTool.
    """

    def getEncoding():

        """ Get the encoding used for configuration data within the site.

        o Return None if the data should not be encoded.
        """

    def getImportContextID():

        """ Get the ID of the active import context.
        """

    def applyContext( context, encoding=None ):

        """ Update the tool from the supplied context, without modifying its
            "permanent" ID.
        """

    def setImportContext( context_id ):

        """ Set the ID of the active import context and update the registries.
        """

    def getImportStepRegistry():

        """ Return the IImportStepRegistry for the tool.
        """

    def getExportStepRegistry():

        """ Return the IExportStepRegistry for the tool.
        """

    def getToolsetRegistry():

        """ Return the IToolsetRegistry for the tool.
        """

    def runImportStep( step_id, run_dependencies=True, purge_old=None ):

        """ Execute a given setup step

        o 'step_id' is the ID of the step to run.

        o If 'purge_old' is True, then run the step after purging any
          "old" setup first (this is the responsibility of the step,
          which must check the context we supply).

        o If 'run_dependencies' is True, then run any out-of-date
          dependency steps first.

        o Return a mapping, with keys:

          'steps' -- a sequence of IDs of the steps run.

          'messages' -- a dictionary holding messages returned from each
            step
        """

    def runAllImportSteps( purge_old=None ):

        """ Run all setup steps in dependency order.

        o If 'purge_old' is True, then run each step after purging any
          "old" setup first (this is the responsibility of the step,
          which must check the context we supply).

        o Return a mapping, with keys:

          'steps' -- a sequence of IDs of the steps run.

          'messages' -- a dictionary holding messages returned from each
            step
        """

    def runExportStep( step_id ):

        """ Generate a tarball containing artifacts from one export step.

        o 'step_id' identifies the export step.

        o Return a mapping, with keys:

          'steps' -- a sequence of IDs of the steps run.

          'messages' -- a dictionary holding messages returned from each
            step

          'tarball' -- the stringified tar-gz data.
        """

    def runAllExportSteps():

        """ Generate a tarball containing artifacts from all export steps.

        o Return a mapping, with keys:

          'steps' -- a sequence of IDs of the steps run.

          'messages' -- a dictionary holding messages returned from each
            step

          'tarball' -- the stringified tar-gz data.
        """

    def createSnapshot( snapshot_id ):

        """ Create a snapshot folder using all steps.

        o 'snapshot_id' is the ID of the new folder.
        """

    def compareConfigurations( lhs_context
                             , rhs_context
                             , missing_as_empty=False
                             , ignore_whitespace=False
                             ):
        """ Compare two configurations.

        o 'lhs_context' and 'rhs_context' must implement IImportContext.

        o If 'missing_as_empty', then compare files not present as though
          they were zero-length;  otherwise, omit such files.

        o If 'ignore_whitespace', then suppress diffs due only to whitespace
          (c.f:  'diff -wbB')
        """


class IWriteLogger(Interface):

    """Write methods used by the python logging Logger.
    """

    def debug(msg, *args, **kwargs):
        """Log 'msg % args' with severity 'DEBUG'.
        """

    def info(msg, *args, **kwargs):
        """Log 'msg % args' with severity 'INFO'.
        """

    def warning(msg, *args, **kwargs):
        """Log 'msg % args' with severity 'WARNING'.
        """

    def error(msg, *args, **kwargs):
        """Log 'msg % args' with severity 'ERROR'.
        """

    def exception(msg, *args):
        """Convenience method for logging an ERROR with exception information.
        """

    def critical(msg, *args, **kwargs):
        """Log 'msg % args' with severity 'CRITICAL'.
        """

    def log(level, msg, *args, **kwargs):
        """Log 'msg % args' with the integer severity 'level'.
        """


class INode(Interface):

    """Node im- and exporter.
    """

    node = Text(description=u'Im- and export the object as a DOM node.')


class IBody(INode):

    """Body im- and exporter.
    """

    body = Text(description=u'Im- and export the object as a file body.')

    mime_type = TextLine(description=u'MIME type of the file body.')

    name = TextLine(description=u'Enforce this name for the file.')

    suffix = TextLine(description=u'Suffix for the file.')


class IFilesystemExporter(Interface):
    """ Plugin interface for site structure export.
    """
    def export(export_context, subdir, root=False):
        """ Export our 'context' using the API of 'export_context'.

        o 'export_context' must implement
          Products.GenericSupport.interfaces.IExportContext.

        o 'subdir', if passed, is the relative subdirectory containing our
          context within the site.

        o 'root', if true, indicates that the current context is the
          "root" of an import (this may be used to adjust paths when
          interacting with the context).
        """

    def listExportableItems():
        """ Return a sequence of the child items to be exported.

        o Each item in the returned sequence will be a tuple,
          (id, object, adapter) where adapter must implement
          IFilesystemExporter.
        """

class IFilesystemImporter(Interface):
    """ Plugin interface for site structure export.
    """
    def import_(import_context, subdir, root=False):
        """ Import our 'context' using the API of 'import_context'.

        o 'import_context' must implement
          Products.GenericSupport.interfaces.IImportContext.

        o 'subdir', if passed, is the relative subdirectory containing our
          context within the site.

        o 'root', if true, indicates that the current context is the
          "root" of an import (this may be used to adjust paths when
          interacting with the context).
        """

class IContentFactory(Interface):
    """ Adapter interface for factories specific to a container.
    """
    def __call__(id):
        """ Return a new instance, seated in the context under 'id'.
        """

class IContentFactoryName(Interface):
    """ Adapter interface for finding the name of the ICF for an object.
    """
    def __call__():
        """ Return a string, suitable for looking up an IContentFactory.
        
        o The string should allow finding a factory for our context's
          container which would create an "empty" instance of the same
          type as our context.
        """

class ICSVAware(Interface):
    """ Interface for objects which dump / load 'text/comma-separated-values'.
    """
    def getId():
        """ Return the Zope id of the object.
        """

    def as_csv():
        """ Return a string representing the object as CSV.
        """

    def put_csv(fd):
        """ Parse CSV and update the object.

        o 'fd' must be a file-like object whose 'read' method returns
          CSV text parseable by the 'csv.reader'.
        """

class IINIAware(Interface):
    """ Interface for objects which dump / load INI-format files..
    """
    def getId():
        """ Return the Zope id of the object.
        """

    def as_ini():
        """ Return a string representing the object as INI.
        """

    def put_ini(stream_or_text):
        """ Parse INI-formatted text and update the object.

        o 'stream_or_text' must be either a string, or else a stream
          directly parseable by ConfigParser.
        """

class IDAVAware(Interface):
    """ Interface for objects which handle their own FTP / DAV operations.
    """
    def getId():
        """ Return the Zope id of the object.
        """

    def manage_FTPget():
        """ Return a string representing the object as a file.
        """

    def PUT(REQUEST, RESPONSE):
        """ Parse file content and update the object.

        o 'REQUEST' will have a 'get' method, which will have the 
          content object in its "BODY" key.  It will also have 'get_header'
          method, whose headers (e.g., "Content-Type") may affect the
          processing of the body.
        """
