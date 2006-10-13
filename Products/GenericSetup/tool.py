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
""" Classes:  SetupTool

$Id: tool.py 70268 2006-09-20 21:07:49Z tseaver $
"""

import os
import time
from cgi import escape

from AccessControl import ClassSecurityInfo
from Acquisition import aq_base
from Globals import InitializeClass
from OFS.Folder import Folder
from OFS.Image import File
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from zope.interface import implements
from zope.interface import implementedBy

from interfaces import EXTENSION
from interfaces import ISetupTool
from interfaces import SKIPPED_FILES
from permissions import ManagePortal
from context import DirectoryImportContext
from context import SnapshotImportContext
from context import TarballExportContext
from context import TarballImportContext
from context import SnapshotExportContext
from differ import ConfigDiff
from registry import ImportStepRegistry
from registry import ExportStepRegistry
from registry import ToolsetRegistry
from registry import _profile_registry

from utils import _resolveDottedName
from utils import _wwwdir

IMPORT_STEPS_XML = 'import_steps.xml'
EXPORT_STEPS_XML = 'export_steps.xml'
TOOLSET_XML = 'toolset.xml'

def exportStepRegistries(context):

    """ Built-in handler for exporting import / export step registries.
    """
    setup_tool = context.getSetupTool()
    logger = context.getLogger('registries')

    import_steps_xml = setup_tool.getImportStepRegistry().generateXML()
    context.writeDataFile('import_steps.xml', import_steps_xml, 'text/xml')

    export_steps_xml = setup_tool.getExportStepRegistry().generateXML()
    context.writeDataFile('export_steps.xml', export_steps_xml, 'text/xml')

    logger.info('Step registries exported.')

def importToolset(context):

    """ Import required / forbidden tools from XML file.
    """
    site = context.getSite()
    encoding = context.getEncoding()
    logger = context.getLogger('toolset')

    xml = context.readDataFile(TOOLSET_XML)
    if xml is None:
        logger.info('Nothing to import.')
        return

    setup_tool = context.getSetupTool()
    toolset = setup_tool.getToolsetRegistry()

    toolset.parseXML(xml, encoding)

    existing_ids = site.objectIds()
    existing_values = site.objectValues()

    for tool_id in toolset.listForbiddenTools():

        if tool_id in existing_ids:
            site._delObject(tool_id)

    for info in toolset.listRequiredToolInfo():

        tool_id = str(info['id'])
        tool_class = _resolveDottedName(info['class'])

        existing = getattr(aq_base(site), tool_id, None)
        try:
            new_tool = tool_class()
        except TypeError:
            new_tool = tool_class(tool_id)
        else:
            try:
                new_tool._setId(tool_id)
            except: # XXX:  ImmutableId raises result of calling MessageDialog
                pass

        if existing is None:
            site._setObject(tool_id, new_tool)

        else:
            unwrapped = aq_base(existing)
            if not isinstance(unwrapped, tool_class):
                site._delObject(tool_id)
                site._setObject(tool_id, tool_class())

    logger.info('Toolset imported.')

def exportToolset(context):

    """ Export required / forbidden tools to XML file.
    """
    setup_tool = context.getSetupTool()
    toolset = setup_tool.getToolsetRegistry()
    logger = context.getLogger('toolset')

    xml = toolset.generateXML()
    context.writeDataFile(TOOLSET_XML, xml, 'text/xml')

    logger.info('Toolset exported.')


class SetupTool(Folder):

    """ Profile-based site configuration manager.
    """

    implements(ISetupTool)

    meta_type = 'Generic Setup Tool'

    _import_context_id = ''

    security = ClassSecurityInfo()

    def __init__(self, id):
        self.id = str(id)
        self._import_registry = ImportStepRegistry()
        self._export_registry = ExportStepRegistry()
        self._export_registry.registerStep('step_registries',
                                           exportStepRegistries,
                                           'Export import / export steps.',
                                          )
        self._toolset_registry = ToolsetRegistry()

    #
    #   ISetupTool API
    #
    security.declareProtected(ManagePortal, 'getEncoding')
    def getEncoding(self):

        """ See ISetupTool.
        """
        return 'ascii'

    security.declareProtected(ManagePortal, 'getImportContextID')
    def getImportContextID(self):

        """ See ISetupTool.
        """
        return self._import_context_id

    security.declareProtected(ManagePortal, 'setImportContext')
    def setImportContext(self, context_id, encoding=None):

        """ See ISetupTool.
        """
        self._import_context_id = context_id
        context = self._getImportContext(context_id)

        self.applyContext(context, encoding)

    security.declareProtected(ManagePortal, 'applyContext')
    def applyContext(self, context, encoding=None):
        self._updateImportStepsRegistry(context, encoding)
        self._updateExportStepsRegistry(context, encoding)
        self._updateToolsetRegistry(context, encoding)

    security.declareProtected(ManagePortal, 'getImportStepRegistry')
    def getImportStepRegistry(self):

        """ See ISetupTool.
        """
        return self._import_registry

    security.declareProtected(ManagePortal, 'getExportStepRegistry')
    def getExportStepRegistry(self):

        """ See ISetupTool.
        """
        return self._export_registry

    security.declareProtected(ManagePortal, 'getToolsetRegistry')
    def getToolsetRegistry(self):

        """ See ISetupTool.
        """
        return self._toolset_registry

    security.declareProtected(ManagePortal, 'runImportStep')
    def runImportStep(self, step_id, run_dependencies=True, purge_old=None):

        """ See ISetupTool.
        """
        context = self._getImportContext(self._import_context_id, purge_old)

        info = self._import_registry.getStepMetadata(step_id)

        if info is None:
            raise ValueError, 'No such import step: %s' % step_id

        dependencies = info.get('dependencies', ())

        messages = {}
        steps = []
        if run_dependencies:
            for dependency in dependencies:

                if dependency not in steps:
                    message = self._doRunImportStep(dependency, context)
                    messages[dependency] = message or ''
                    steps.append(dependency)

        message = self._doRunImportStep(step_id, context)
        message_list = filter(None, [message])
        message_list.extend( ['%s: %s' % x[1:] for x in context.listNotes()] )
        messages[step_id] = '\n'.join(message_list)
        steps.append(step_id)

        return { 'steps' : steps, 'messages' : messages }

    security.declareProtected(ManagePortal, 'runAllImportSteps')
    def runAllImportSteps(self, purge_old=None):

        """ See ISetupTool.
        """
        __traceback_info__ = self._import_context_id

        context = self._getImportContext(self._import_context_id, purge_old)

        return self._runImportStepsFromContext(context, purge_old=purge_old)

    security.declareProtected(ManagePortal, 'runExportStep')
    def runExportStep(self, step_id):

        """ See ISetupTool.
        """
        return self._doRunExportSteps([step_id])

    security.declareProtected(ManagePortal, 'runAllExportSteps')
    def runAllExportSteps(self):

        """ See ISetupTool.
        """
        return self._doRunExportSteps(self._export_registry.listSteps())

    security.declareProtected(ManagePortal, 'createSnapshot')
    def createSnapshot(self, snapshot_id):

        """ See ISetupTool.
        """
        context = SnapshotExportContext(self, snapshot_id)
        messages = {}
        steps = self._export_registry.listSteps()

        for step_id in steps:

            handler = self._export_registry.getStep(step_id)

            if handler is None:
                raise ValueError('Invalid export step: %s' % step_id)

            messages[step_id] = handler(context)


        return { 'steps' : steps
               , 'messages' : messages
               , 'url' : context.getSnapshotURL()
               , 'snapshot' : context.getSnapshotFolder()
               }

    security.declareProtected(ManagePortal, 'compareConfigurations')
    def compareConfigurations(self,
                              lhs_context,
                              rhs_context,
                              missing_as_empty=False,
                              ignore_blanks=False,
                              skip=SKIPPED_FILES,
                             ):
        """ See ISetupTool.
        """
        differ = ConfigDiff(lhs_context,
                            rhs_context,
                            missing_as_empty,
                            ignore_blanks,
                            skip,
                           )

        return differ.compare()

    security.declareProtected(ManagePortal, 'markupComparison')
    def markupComparison(self, lines):

        """ See ISetupTool.
        """
        result = []

        for line in lines.splitlines():

            if line.startswith('** '):

                if line.find('File') > -1:
                    if line.find('replaced') > -1:
                        result.append(('file-to-dir', line))
                    elif line.find('added') > -1:
                        result.append(('file-added', line))
                    else:
                        result.append(('file-removed', line))
                else:
                    if line.find('replaced') > -1:
                        result.append(('dir-to-file', line))
                    elif line.find('added') > -1:
                        result.append(('dir-added', line))
                    else:
                        result.append(('dir-removed', line))

            elif line.startswith('@@'):
                result.append(('diff-range', line))

            elif line.startswith(' '):
                result.append(('diff-context', line))

            elif line.startswith('+'):
                result.append(('diff-added', line))

            elif line.startswith('-'):
                result.append(('diff-removed', line))

            elif line == '\ No newline at end of file':
                result.append(('diff-context', line))

            else:
                result.append(('diff-header', line))

        return '<pre>\n%s\n</pre>' % (
            '\n'.join([('<span class="%s">%s</span>' % (cl, escape(l)))
                                  for cl, l in result]))

    #
    #   ZMI
    #
    manage_options = (Folder.manage_options[:1]
                    + ({'label' : 'Properties',
                        'action' : 'manage_tool'
                       },
                       {'label' : 'Import',
                        'action' : 'manage_importSteps'
                       },
                       {'label' : 'Export',
                        'action' : 'manage_exportSteps'
                       },
                       {'label' : 'Snapshots',
                        'action' : 'manage_snapshots'
                       },
                       {'label' : 'Comparison',
                        'action' : 'manage_showDiff'
                       },
                      )
                    + Folder.manage_options[3:] # skip "View", "Properties"
                     )

    security.declareProtected(ManagePortal, 'manage_tool')
    manage_tool = PageTemplateFile('sutProperties', _wwwdir)

    security.declareProtected(ManagePortal, 'manage_updateToolProperties')
    def manage_updateToolProperties(self, context_id, RESPONSE):
        """ Update the tool's settings.
        """
        self.setImportContext(context_id)

        RESPONSE.redirect('%s/manage_tool?manage_tabs_message=%s'
                         % (self.absolute_url(), 'Properties+updated.'))

    security.declareProtected(ManagePortal, 'manage_importSteps')
    manage_importSteps = PageTemplateFile('sutImportSteps', _wwwdir)

    security.declareProtected(ManagePortal, 'manage_importSelectedSteps')
    def manage_importSelectedSteps(self,
                                   ids,
                                   run_dependencies,
                                   RESPONSE,
                                   create_report=True,
                                  ):
        """ Import the steps selected by the user.
        """
        messages = {}
        if not ids:
            summary = 'No steps selected.'

        else:
            steps_run = []
            for step_id in ids:
                result = self.runImportStep(step_id, run_dependencies)
                steps_run.extend(result['steps'])
                messages.update(result['messages'])

            summary = 'Steps run: %s' % ', '.join(steps_run)

            if create_report:
                name = self._mangleTimestampName('import-selected', 'log')
                self._createReport(name, result['steps'], result['messages'])

        return self.manage_importSteps(manage_tabs_message=summary,
                                       messages=messages)

    security.declareProtected(ManagePortal, 'manage_importSelectedSteps')
    def manage_importAllSteps(self, RESPONSE, create_report=True):

        """ Import all steps.
        """
        result = self.runAllImportSteps()
        steps_run = 'Steps run: %s' % ', '.join(result['steps'])

        if create_report:
            name = self._mangleTimestampName('import-all', 'log')
            self._createReport(name, result['steps'], result['messages'])

        return self.manage_importSteps(manage_tabs_message=steps_run,
                                       messages=result['messages'])

    security.declareProtected(ManagePortal, 'manage_importTarball')
    def manage_importTarball(self, tarball, RESPONSE, create_report=True):
        """ Import steps from the uploaded tarball.
        """
        if getattr(tarball, 'read', None) is not None:
            tarball = tarball.read()

        context = TarballImportContext(tool=self,
                                       archive_bits=tarball,
                                       encoding='UTF8',
                                       should_purge=True,
                                      )
        result = self._runImportStepsFromContext(context,
                                                 purge_old=True)
        steps_run = 'Steps run: %s' % ', '.join(result['steps'])

        if create_report:
            name = self._mangleTimestampName('import-all', 'log')
            self._createReport(name, result['steps'], result['messages'])

        return self.manage_importSteps(manage_tabs_message=steps_run,
                                       messages=result['messages'])

    security.declareProtected(ManagePortal, 'manage_exportSteps')
    manage_exportSteps = PageTemplateFile('sutExportSteps', _wwwdir)

    security.declareProtected(ManagePortal, 'manage_exportSelectedSteps')
    def manage_exportSelectedSteps(self, ids, RESPONSE):

        """ Export the steps selected by the user.
        """
        if not ids:
            RESPONSE.redirect('%s/manage_exportSteps?manage_tabs_message=%s'
                             % (self.absolute_url(), 'No+steps+selected.'))

        result = self._doRunExportSteps(ids)
        RESPONSE.setHeader('Content-type', 'application/x-gzip')
        RESPONSE.setHeader('Content-disposition',
                           'attachment; filename=%s' % result['filename'])
        return result['tarball']

    security.declareProtected(ManagePortal, 'manage_exportAllSteps')
    def manage_exportAllSteps(self, RESPONSE):

        """ Export all steps.
        """
        result = self.runAllExportSteps()
        RESPONSE.setHeader('Content-type', 'application/x-gzip')
        RESPONSE.setHeader('Content-disposition',
                           'attachment; filename=%s' % result['filename'])
        return result['tarball']

    security.declareProtected(ManagePortal, 'manage_snapshots')
    manage_snapshots = PageTemplateFile('sutSnapshots', _wwwdir)

    security.declareProtected(ManagePortal, 'listSnapshotInfo')
    def listSnapshotInfo(self):

        """ Return a list of mappings describing available snapshots.

        o Keys include:

          'id' -- snapshot ID

          'title' -- snapshot title or ID

          'url' -- URL of the snapshot folder
        """
        result = []
        snapshots = self._getOb('snapshots', None)

        if snapshots:

            for id, folder in snapshots.objectItems('Folder'):

                result.append({ 'id' : id
                               , 'title' : folder.title_or_id()
                               , 'url' : folder.absolute_url()
                               })
        return result

    security.declareProtected(ManagePortal, 'listProfileInfo')
    def listProfileInfo(self):

        """ Return a list of mappings describing registered profiles.

        o Keys include:

          'id' -- profile ID

          'title' -- profile title or ID

          'description' -- description of the profile

          'path' -- path to the profile within its product

          'product' -- name of the registering product
        """
        return _profile_registry.listProfileInfo()

    security.declareProtected(ManagePortal, 'listContextInfos')
    def listContextInfos(self):

        """ List registered profiles and snapshots.
        """

        s_infos = [{ 'id': 'snapshot-%s' % info['id'],
                      'title': info['title'] }
                    for info in self.listSnapshotInfo()]
        p_infos = [{ 'id': 'profile-%s' % info['id'],
                      'title': info['title'] }
                    for info in self.listProfileInfo()]

        return tuple(s_infos + p_infos)

    security.declareProtected(ManagePortal, 'manage_createSnapshot')
    def manage_createSnapshot(self, RESPONSE, snapshot_id=None):

        """ Create a snapshot with the given ID.

        o If no ID is passed, generate one.
        """
        if snapshot_id is None:
            snapshot_id = self._mangleTimestampName('snapshot')

        self.createSnapshot(snapshot_id)

        RESPONSE.redirect('%s/manage_snapshots?manage_tabs_message=%s'
                         % (self.absolute_url(), 'Snapshot+created.'))

    security.declareProtected(ManagePortal, 'manage_showDiff')
    manage_showDiff = PageTemplateFile('sutCompare', _wwwdir)

    def manage_downloadDiff(self,
                            lhs,
                            rhs,
                            missing_as_empty,
                            ignore_blanks,
                            RESPONSE,
                           ):
        """ Crack request vars and call compareConfigurations.

        o Return the result as a 'text/plain' stream, suitable for framing.
        """
        comparison = self.manage_compareConfigurations(lhs,
                                                       rhs,
                                                       missing_as_empty,
                                                       ignore_blanks,
                                                      )
        RESPONSE.setHeader('Content-Type', 'text/plain')
        return _PLAINTEXT_DIFF_HEADER % (lhs, rhs, comparison)

    security.declareProtected(ManagePortal, 'manage_compareConfigurations')
    def manage_compareConfigurations(self,
                                     lhs,
                                     rhs,
                                     missing_as_empty,
                                     ignore_blanks,
                                    ):
        """ Crack request vars and call compareConfigurations.
        """
        lhs_context = self._getImportContext(lhs)
        rhs_context = self._getImportContext(rhs)

        return self.compareConfigurations(lhs_context,
                                          rhs_context,
                                          missing_as_empty,
                                          ignore_blanks,
                                         )


    #
    #   Helper methods
    #
    security.declarePrivate('_getProductPath')
    def _getProductPath(self, product_name):

        """ Return the absolute path of the product's directory.
        """
        try:
            # BBB: for GenericSetup 1.1 style product names
            product = __import__('Products.%s' % product_name
                                , globals(), {}, ['initialize'])
        except ImportError:
            try:
                product = __import__(product_name
                                    , globals(), {}, ['initialize'])
            except ImportError:
                raise ValueError('Not a valid product name: %s'
                                 % product_name)

        return product.__path__[0]

    security.declarePrivate('_getImportContext')
    def _getImportContext(self, context_id, should_purge=None):

        """ Crack ID and generate appropriate import context.
        """
        encoding = self.getEncoding()

        if context_id.startswith('profile-'):

            context_id = context_id[len('profile-'):]
            info = _profile_registry.getProfileInfo(context_id)

            if info.get('product'):
                path = os.path.join(self._getProductPath(info['product'])
                                   , info['path'])
            else:
                path = info['path']
            if should_purge is None:
                should_purge = (info.get('type') != EXTENSION)
            return DirectoryImportContext(self, path, should_purge, encoding)

        # else snapshot
        context_id = context_id[len('snapshot-'):]
        if should_purge is None:
            should_purge = True
        return SnapshotImportContext(self, context_id, should_purge, encoding)

    security.declarePrivate('_updateImportStepsRegistry')
    def _updateImportStepsRegistry(self, context, encoding):

        """ Update our import steps registry from our profile.
        """
        if context is None:
            context = self._getImportContext(self._import_context_id)
        xml = context.readDataFile(IMPORT_STEPS_XML)
        if xml is None:
            return

        info_list = self._import_registry.parseXML(xml, encoding)

        for step_info in info_list:

            id = step_info['id']
            version = step_info['version']
            handler = _resolveDottedName(step_info['handler'])

            dependencies = tuple(step_info.get('dependencies', ()))
            title = step_info.get('title', id)
            description = ''.join(step_info.get('description', []))

            self._import_registry.registerStep(id=id,
                                               version=version,
                                               handler=handler,
                                               dependencies=dependencies,
                                               title=title,
                                               description=description,
                                              )

    security.declarePrivate('_updateExportStepsRegistry')
    def _updateExportStepsRegistry(self, context, encoding):

        """ Update our export steps registry from our profile.
        """
        if context is None:
            context = self._getImportContext(self._import_context_id)
        xml = context.readDataFile(EXPORT_STEPS_XML)
        if xml is None:
            return

        info_list = self._export_registry.parseXML(xml, encoding)

        for step_info in info_list:

            id = step_info['id']
            handler = _resolveDottedName(step_info['handler'])

            title = step_info.get('title', id)
            description = ''.join(step_info.get('description', []))

            self._export_registry.registerStep(id=id,
                                               handler=handler,
                                               title=title,
                                               description=description,
                                              )

    security.declarePrivate('_updateToolsetRegistry')
    def _updateToolsetRegistry(self, context, encoding):

        """ Update our toolset registry from our profile.
        """
        if context is None:
            context = self._getImportContext(self._import_context_id)
        xml = context.readDataFile(TOOLSET_XML)
        if xml is None:
            return

        self._toolset_registry.parseXML(xml, encoding)

    security.declarePrivate('_doRunImportStep')
    def _doRunImportStep(self, step_id, context):

        """ Run a single import step, using a pre-built context.
        """
        __traceback_info__ = step_id

        handler = self._import_registry.getStep(step_id)

        if handler is None:
            raise ValueError('Invalid import step: %s' % step_id)

        return handler(context)

    security.declarePrivate('_doRunExportSteps')
    def _doRunExportSteps(self, steps):

        """ See ISetupTool.
        """
        context = TarballExportContext(self)
        messages = {}

        for step_id in steps:

            handler = self._export_registry.getStep(step_id)

            if handler is None:
                raise ValueError('Invalid export step: %s' % step_id)

            messages[step_id] = handler(context)

        return { 'steps' : steps
               , 'messages' : messages
               , 'tarball' : context.getArchive()
               , 'filename' : context.getArchiveFilename()
               }

    security.declarePrivate('_runImportStepsFromContext')
    def _runImportStepsFromContext(self, context, steps=None, purge_old=None):
        self.applyContext(context)

        if steps is None:
            steps = self._import_registry.sortSteps()
        messages = {}

        for step in steps:
            message = self._doRunImportStep(step, context)
            message_list = filter(None, [message])
            message_list.extend( ['%s: %s' % x[1:]
                                  for x in context.listNotes()] )
            messages[step] = '\n'.join(message_list)
            context.clearNotes()

        return { 'steps' : steps, 'messages' : messages }

    security.declarePrivate('_mangleTimestampName')
    def _mangleTimestampName(self, prefix, ext=None):

        """ Create a mangled ID using a timestamp.
        """
        timestamp = time.gmtime()
        items = (prefix,) + timestamp[:6]

        if ext is None:
            fmt = '%s-%4d%02d%02d%02d%02d%02d'
        else:
            fmt = '%s-%4d%02d%02d%02d%02d%02d.%s'
            items += (ext,)

        return fmt % items

    security.declarePrivate('_createReport')
    def _createReport(self, name, steps, messages):

        """ Record the results of a run.
        """
        lines = []
        # Create report
        for step in steps:
            lines.append('=' * 65)
            lines.append('Step: %s' % step)
            lines.append('=' * 65)
            msg = messages[step]
            lines.extend(msg.split('\n'))
            lines.append('')

        report = '\n'.join(lines)
        if isinstance(report, unicode):
            report = report.encode('latin-1')

        file = File(id=name,
                    title='',
                    file=report,
                    content_type='text/plain'
                   )
        self._setObject(name, file)

InitializeClass(SetupTool)

_PLAINTEXT_DIFF_HEADER ="""\
Comparing configurations: '%s' and '%s'

%s"""

_TOOL_ID = 'setup_tool'

addSetupToolForm = PageTemplateFile('toolAdd.zpt', _wwwdir)

def addSetupTool(dispatcher, RESPONSE):
    """
    """
    dispatcher._setObject(_TOOL_ID, SetupTool(_TOOL_ID))

    RESPONSE.redirect('%s/manage_main' % dispatcher.absolute_url())
