##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """zenmib
   The zenmib program converts MIBs into python data structures and then
(by default) adds the data to the Zenoss DMD.  Essentially, zenmib is a
wrapper program around the smidump program, whose output (python code) is
then executed "inside" the Zope database.

 Overview of terms:
   SNMP Simple Network Management Protocol
      A network protocol originally based on UDP which allows a management
      application (ie SNMP manager) to contact and get information from a
      device (ie router, computer, network-capable toaster).  The software
      on the device that is capable of understanding SNMP and responding
      appropriately is called an SNMP agent.

   MIB Management of Information Base
      A description of what a particular SNMP agent provides and what
      traps it sends.  A MIB is a part of a tree structure based on a root
      MIB.  Since a MIB is a rooted tree, it allows for delegation of areas
      under the tree to different organizations.

   ASN Abstract Syntax Notation
      The notation used to construct a MIB.

   OID Object IDentifier
      A MIB is constructed of unique identifiers


 Background information:
   http://en.wikipedia.org/wiki/Simple_Network_Management_Protocol
       Overview of SNMP.

   http://www.ibr.cs.tu-bs.de/projects/libsmi/index.html?lang=en
       The libsmi project is the creator of smidump.  There are several
       interesting sub-projects available.

   http://net-snmp.sourceforge.net/
       Homepage for Net-SNMP which is used by Zenoss for SNMP management.

   http://www.et.put.poznan.pl/snmp/asn1/asn1.html
       An overview of Abstract Syntax Notation (ASN), the language in
       which MIBs are written.
"""

import os
import os.path
import sys
import re
from subprocess import Popen, PIPE
import tempfile
import urllib
import tarfile
import zipfile
from urlparse import urlsplit
from collections import OrderedDict

import Globals
import transaction

from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.Utils import zenPath
from zExceptions import BadRequest


CHUNK_SIZE = 50

# Used to convert dictionary values in smidump output to raw strings
# "key": "value" becomes "key": r"value"
# This helps exec handle backslashes.
_DICT_STRING_VALUE_PATTERN = re.compile(r'(:\s*)"')

class MibFile(object):
    """
    A MIB file has the meta-data for a MIB inside of it.
    """
    def __init__(self, fileName, fileContents=""):
        self.fileName = fileName
        self.mibs = [] # Order of MIBs defined in the file
        self.mibToDeps = {} # Dependency defintions for each MIB
        self.fileContents = self.removeMibComments(fileContents)
        self.mibDefinitions = self.splitFileToMIBs(self.fileContents)
        self.mapMibToDependents(self.mibDefinitions)

        # Reclaim some memory
        self.fileContents = ""
        self.mibDefinitions = ""

    def removeMibComments(self, fileContents):
        """
        Parses the string provided as an argument and extracts
        all of the ASN.1 comments from the string.

        Assumes that fileContents contains the contents of a well-formed
        (no errors) MIB file.

        @param fileContents: entire contents of a MIB file
        @type fileContents: string
        @return: text without any comments
        @rtype: string
        """
        if not fileContents:
            return fileContents

        cursor = 0
        fc = []
        while cursor < len(fileContents):
            searchParty = [ fileContents.find('"',cursor), fileContents.find('/*',cursor), fileContents.find('--',cursor) ]
            try:
                cursor = min( x for x in searchParty if x >= 0 )
            except ValueError:
                break

            if searchParty[0] == cursor:
                '''
                MIB block quote rules
                1.  Begins with '"'
                2.  Ends with '"'
                3.  Quotes can be nested with '""'
                4.  Any characters between the beginning and the end of the string
                    are considered part of the string.  All comment characters like
                    ('--') and ('/*...*/') are not ignored.  Newlines are included
                    in the blockquote
                '''
                cursor = fileContents.find('"',cursor+1) + 1
                while 0 < cursor < len(fileContents) and fileContents[cursor] == '"':
                    cursor = fileContents.find('"', cursor + 1) + 1

                # Syntax error if no close quote found
                if not cursor:
                    raise ValueError("Syntax Error: missing close (\")")

                continue
            elif searchParty[1] == cursor:
                '''
                MIB block comment rules:
                1.  Begins with '/*'
                2.  Ends with '*/'
                3.  Block comments can be nested
                4.  Any characters between the beginning and end of the comment
                    are ignored as part of the comment, including quotes and
                    start/end delimiters for single line comments ('--'). Newlines
                    are included as part of the block comment.
                '''
                endComment = fileContents.find("*/",cursor+2)
                if endComment < 0:
                    raise ValueError("Syntax Error: missing close (*/)")

                nestCount = 1
                # Check for a nested block
                while nestCount != fileContents.count("/*", cursor, endComment):

                    # Corner case for /*/
                    if fileContents[endComment-1] == '/':
                        fc_list = list(fileContents)
                        fc_list[endComment-1] = ' '
                        fileContents = ''.join(fc_list)
                    endComment = fileContents.find("*/", endComment+2)
                    if endComment < 0:
                        raise ValueError("Syntax Error: missing close (*/)")

                    nestCount += 1

                endComment += 2
            elif searchParty[2] == cursor:
                '''
                MIB single line comment rules:
                1.  Begins with '--'
                2.  Ends with '--' or newline
                3.  Any characters between the beginning and end of the comment
                    are ignored as part of the comment, including quotes and
                    start/end delimiters for block comments ( '/*' and '*/')
                '''
                endComment = fileContents.find('\n',cursor+2)

                #EOF reached
                if endComment < 0:
                    endComment = len(fileContents)

                # Ignore dash lines
                dashline = fileContents[cursor:endComment].strip()
                if dashline != '-' * len(dashline):
                    ec = fileContents.find('--', cursor+2, endComment)
                    if ec > -1:
                        endComment = ec+2

            fc.append(fileContents[:cursor])
            fileContents = fileContents[endComment:]
            cursor = 0

        fc.append(fileContents)
        return ''.join(fc)

    def splitFileToMIBs(self, fileContents):
        """
        Isolates each MIB definition in fileContents into a separate string

        @param fileContents: the complete contents of a MIB file
        @type fileContents: string
        @return: MIB definition strings
        @rtype: list of strings
        """
        if fileContents is None:
            return []

        DEFINITIONS = re.compile(r'([A-Za-z-0-9]+\s+DEFINITIONS'
            '(\s+EXPLICIT TAGS|\s+IMPLICIT TAGS|\s+AUTOMATIC TAGS|\s*)'
            '(\s+EXTENSIBILITY IMPLIED|\s*)\s*::=\s*BEGIN)')

        definitionSpans = []
        for definitionMatch in DEFINITIONS.finditer(fileContents):
            definitionSpans.append(list(definitionMatch.span()))
            # If more than one definiton in the file, set the end of the
            # last span to the beginning of the current span
            if len(definitionSpans) > 1:
                definitionSpans[-2][1] = definitionSpans[-1][0]

        # Use the start and end positions to create a string for each
        # MIB definition
        mibDefinitions = []
        if definitionSpans:
            # Set the end of the last span to the end of the file
            definitionSpans[-1][1] = len(fileContents)
            for definitionSpan in definitionSpans:
                mibDefinitions.append(
                    fileContents[definitionSpan[0]:definitionSpan[1]])

        return mibDefinitions

    def mapMibToDependents(self, mibDefinitions):
        # ASN.1 syntax regular expressions for declaring MIBs
        #
        # An example from http://www.faqs.org/rfcs/rfc1212.html
        #
        # RFC1213-MIB DEFINITIONS ::= BEGIN
        #
        # IMPORTS
        #        experimental, OBJECT-TYPE, Counter
        #             FROM RFC1155-SMI;
        #
        #     -- a MIB may or may not have an IMPORTS section
        #
        # root    OBJECT IDENTIFIER ::= { experimental xx }
        #
        # END
        IMPORTS = re.compile(r'\sIMPORTS\s.+;', re.DOTALL)
        DEPENDENCIES = re.compile(
            r'\sFROM\s+(?P<dependency>[A-Za-z-0-9]+)')

        for definition in mibDefinitions:
            mibName = re.split(r'([A-Za-z0-9-]+)', definition)[1]
            dependencies = set()
            importsMatch = IMPORTS.search(definition)
            if importsMatch:
                imports = importsMatch.group()
                for dependencyMatch in DEPENDENCIES.finditer(imports):
                    dependencies.add(dependencyMatch.group('dependency'))
            self.mibs.append(mibName)
            self.mibToDeps[mibName] = dependencies

class PackageManager:
    """
    Given an URL, filename or archive (eg zip, tar), extract the files from
    the package and return a list of filenames.
    """
    def __init__(self, log, downloaddir, extractdir):
        """
        Initialize the packagae manager.

        @parameter log: logging object
        @type log: logging class object
        @parameter downloaddir: directory name to store downloads
        @type downloaddir: string
        @parameter extractdir: directory name to store downloads
        @type extractdir: string
        """
        self.log = log
        self.downloaddir = downloaddir
        if self.downloaddir[-1] != '/':
            self.downloaddir += '/'
        self.extractdir = extractdir
        if self.extractdir[-1] != '/':
            self.extractdir += '/'

    def downloadExtract(self, url):
        """
        Download and extract the list of filenames.
        """
        try:
            localFile = self.download(url)
        except Exception:
             self.log.error("Problems downloading the file from %s: %s" % (
                url, sys.exc_info()[1] ) )
             return []
        self.log.debug("Will attempt to load %s", localFile)
        try:
            return self.processPackage(localFile)
        except IOError, ex:
            self.log.error("Unable to process '%s' because: %s",
                           localFile, str(ex))
            sys.exit(1)

    def download(self, url):
        """
        Download the package from the given URL, or if it's a filename,
        return the filename.
        """
        urlParts = urlsplit(url)
        schema = urlParts[0]
        path = urlParts[2]
        if not schema:
            return os.path.abspath(url)
        file = path.split(os.sep)[-1]
        os.makedirs(self.downloaddir)
        downloadFile = os.path.join(self.downloaddir, file)
        self.log.debug("Downloading to file '%s'", downloadFile)
        filename, _ = urllib.urlretrieve(url, downloadFile)
        return filename

    def processPackage(self, pkgFileName):
        """
        Figure out what type of file we have and extract out any
        files and then enumerate the file names.
        """
        self.log.debug("Determining file type of %s" % pkgFileName)
        if zipfile.is_zipfile(pkgFileName):
            return self.unbundlePackage(pkgFileName, self.unzip)

        elif tarfile.is_tarfile(pkgFileName):
            return self.unbundlePackage(pkgFileName, self.untar)

        elif os.path.isdir(pkgFileName):
            return self.processDir(pkgFileName)

        else:
            return [ os.path.abspath(pkgFileName) ]

    def unzip(self, file):
        """
        Unzip the given file into the current directory and return
        the directory in which files can be loaded.
        """
        pkgZip= zipfile.ZipFile(file, 'r')
        if pkgZip.testzip() != None:
            self.log.error("File %s is corrupted -- please download again", file)
            return

        for file in pkgZip.namelist():
            self.log.debug("Unzipping file/dir %s..." % file)
            try:
                if re.search(r'/$', file) != None:
                    os.makedirs(file)
                else:
                    contents = pkgZip.read(file)
                    try:
                        unzipped = open(file, "w")
                    except IOError: # Directory missing?
                        os.makedirs(os.path.dirname(file))
                        unzipped = open(file, "w")
                    unzipped.write(contents)
                    unzipped.close()
            except Exception:
                self.log.error("Error in extracting %s because %s" % (
                    file, sys.exc_info()[1] ) )
                return

        return os.getcwd()

    def untar(self, file):
        """
        Given a tar file, extract from the tar into the current directory.
        """
        try:
            self.log.debug("Extracting files from tar...")
            pkgTar = tarfile.open(file, 'r')
            for tarInfo in pkgTar:
                pkgTar.extract(tarInfo)
            pkgTar.close()
        except Exception:
            self.log.error("Error in un-tarring %s because %s" % ( file,
                                                        sys.exc_info()[1] ) )
            return
        return os.getcwd()

    def processDir(self, dir):
        """
        Note all of the files in a directory.
        """
        fileList = []
        self.log.debug("Enumerating files in %s", dir)
        if not os.path.isdir(dir):
            self.log.debug("%s is not a directory", dir)
            return []
        for directoryName, _, fileNames in os.walk(dir):
            for fileName in fileNames:
                fileList.append(os.path.join(directoryName, fileName))
        return fileList

    def unbundlePackage(self, package, unpackageMethod):
        """
        Extract the files and then add to the list of files.
        """
        self.makeExtractionDir()
        baseDir = unpackageMethod(package)
        if baseDir is not None:
            return self.processDir(baseDir)
        return []

    def makeExtractionDir(self):
        """
        Create an uniquely named extraction directory starting from a base
        extraction directory.
        """
        try:
            if not os.path.isdir(self.extractdir):
                os.makedirs(self.extractdir)
            extractDir = tempfile.mkdtemp(prefix=self.extractdir)
        except Exception:
            self.log.error("Error in creating temp dir because %s",
                                                    sys.exc_info()[1] )
            sys.exit(1)
        os.chdir(extractDir)

    def cleanup(self):
        """
        Remove any clutter left over from the installation.
        """
        self.cleanupDir(self.downloaddir)
        self.cleanupDir(self.extractdir)

    def cleanupDir(self, dirName):
        for root, dirs, files in os.walk(dirName, topdown=False):
            if root == os.sep: # Should *never* get here
                break
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                try:
                    os.removedirs(os.path.join(root, name))
                except OSError:
                    pass
        try:
            os.removedirs(dirName)
        except OSError:
            pass


class ZenMib(ZCmdBase):
    """
    Wrapper around the smidump utilities used to convert MIB definitions into
    python code which is in turn loaded into the DMD tree.
    """
    def makeMibFileObj(self, fileName):
        """
        Scan the MIB file to determine what MIBs are defined in the file and
        what their dependencies are.

        @param fileName: MIB fileName
        @type fileName: string
        @return: dependencyDict, indexDict
            dependencyDict - a dictionary that associates MIB definitions
                found in fileName with their dependencies
            indexDict - a dictionary that associates MIB definitions with their
                ordinal position within fileName}
        @rtype:
            dependencyDict = {mibName: [string list of MIB definition names
                that mibName is dependant on]}
            indexDict = {mibname: number}
        """
        # Retrieve the entire contents of the MIB file
        self.log.debug("Processing %s", fileName)
        file = open(fileName)
        fileContents = file.read()
        file.close()
        return MibFile(fileName, fileContents)

    def populateDependencyMap(self, importFileNames, depFileNames):
        """
        Populates the self.mibToMibFile instance object with data.
        Exit the program if we're missing any files.

        @param importFileNames: fully qualified file names of MIB files to import
        @type importFileNames: list of strings
        @param depFileNames: fully qualified file names of all MIB files
        @type depFileNames: list of strings
        @return: mibFileObjects of files to import
        @rtype: MibFile
        """
        self.log.debug("Collecting MIB meta-data and creating depedency map.")
        toImportMibFileObjs = []
        for fileName in depFileNames.union(importFileNames):
            try:
                mibFileObj = self.makeMibFileObj(fileName)
            except IOError:
                self.log.error("Couldn't open file %s", fileName)
                continue

            mibDependencies = mibFileObj.mibToDeps
            if not mibDependencies:
                self.log.warn("Unable to parse information from "
                    "%s -- skipping", fileName)
                continue

            if fileName in importFileNames:
                toImportMibFileObjs.append(mibFileObj)

            for mibName, dependencies in mibDependencies.items():
                self.mibToMibFile[mibName] = mibFileObj
        return toImportMibFileObjs

    def getDependencyFileNames(self, mibFileObj):
        """
        smidump needs to know the list of dependent files for a MIB file in
        order to properly resolve external references.

        @param mibFileObj: MibFile object
        @type mibFileObj: MibFile
        @return: list of dependency fileNames
        @rtype: list of strings
        """
        dependencies = []
        dependencyFileNames = OrderedDict()

        def dependencySearch(mibName):
            """
            Create a list of files required by a MIB definition.

            @param mibName: name of MIB definition
            @type mibName: string
            """
            dependencies.append(mibName)
            mibFileObj = self.mibToMibFile.get(mibName)
            if not mibFileObj:
                self.log.warn("Unable to find a file that defines %s", mibName)
                return

            dependencyFileNames[mibFileObj.fileName] = None
            for dependency in mibFileObj.mibToDeps[mibName]:
                if dependency not in dependencies:
                    dependencySearch(dependency)

        for mibName in mibFileObj.mibs:
            dependencySearch(mibName)

        if mibFileObj.fileName in dependencyFileNames:
            del dependencyFileNames[mibFileObj.fileName]
        names = dependencyFileNames.keys()
        names.reverse()
        return names

    def savePythonCode(self, pythonCode, fileName):
        """
        Stores the smidump-generated Python code to a file.
        """
        if not os.path.exists(self.options.pythoncodedir):
            self.options.keeppythoncode = False
            self.log.warn('The directory %s to store converted MIB file code '
                'does not exist.' % self.options.pythoncodedir)
            return
        try:
            pythonFileName = os.path.join(self.options.pythoncodedir,
            os.path.basename(fileName) ) + '.py'
            pythonFile = open(pythonFileName, 'w')
            pythonFile.write(pythonCode)
            pythonFile.close()
        except Exception:
            self.log.warn('Could not output converted MIB to %s' %
                pythonFileName)

    def generatePythonFromMib(self, fileName, dependencyFileNames,
            mibNamesInFile):
        """
        Use the smidump program to convert a MIB into Python code.

        One major caveat: smidump by default only outputs the last MIB
        definition in a file. For that matter, it always outputs the last MIB
        definition in a file whether it is requested or not. Therefore, if
        there are multiple MIB definitions in a file, all but the last must be
        explicitly named on the command line. If you name the last, it will
        come out twice. We don't want that.

        OK, so we need to determine if there are multiple MIB definitions
        in fileName and then add all but the last to the command line. That
        works except the resulting python code will create a dictionary
        for each MIB definition, all of them named MIB. Executing the code is
        equivalent to running a=1; a=2; a=3. You only wind up with a=3.
        Therefore, we separate each dictionary definition into its own string
        and return a list of strings so each one can be executed individually.

        @param fileName: name of the file containing MIB definitions
        @type fileName: string
        @param dependencyFileNames: list of fileNames that fileName is
            dependent on
        @type dependencyFileNames: list of strings
        @param mibNamesInFile: names of MIB definitions in file
        @type mibNamesInFile: list of strings
        @return: list of dictionaries. Each dictionary containing the contents
            of a MIB definition. [ {'mibName': MIB data} ]
        @rtype: list
        """
        dumpCommand =  ['smidump', '--keep-going', '--format', 'python']
        for dependencyFileName in dependencyFileNames:
            #  Add command-line flag for our dependent files
            dumpCommand.append('--preload')
            dumpCommand.append(dependencyFileName)
        dumpCommand.append(fileName)

        # If more than one MIB definition exists in the file, name all but the
        # last on the command line. (See method description for reasons.)
        if len(mibNamesInFile) > 1:
            dumpCommand += mibNamesInFile[:-1]

        self.log.debug('Running %s', ' '.join(dumpCommand))
        sys.stdout.flush()
        proc = Popen(dumpCommand, stdout=PIPE, stderr=PIPE, close_fds=True)

        # If the child process generates enough output to the PIPE,
        # then proc.wait() blocks waiting for the OS pipe buffer to accept more data
        # (ie forever).  Poll from time to time to avoid the problem with large MIBs.
        pythonCode = ''
        warnings = ''
        # make sure we always capture the output from the process
        firstPass = True
        while firstPass or proc.poll() is None:
            firstPass = False
            output, err = proc.communicate()
            # convert dictionary values to raw strings
            # "key": "value" becomes "key": r"value"
            pythonCode += _DICT_STRING_VALUE_PATTERN.sub('\g<1>r"', output)
            warnings += err

        if proc.poll() != 0 or proc.returncode:
            if warnings.strip():
                self.log.error(warnings)
            return None

        if warnings:
            self.log.debug("Found warnings while trying to import MIB:\n%s" \
                 % warnings)

        if self.options.keeppythoncode:
            self.savePythonCode(pythonCode, fileName)

        return self.evalPythonToMibs(pythonCode, fileName)

    def evalPythonToMibs(self, pythonCode, name):
        """
        Evaluate the code and return an array of MIB dictionaries.
        """
        def executePythonCode(pythonCode, name):
            """
            Executes the python code generated smidump

            @param pythonCode: Code generated by smidump
            @type pythonCode: string
            @return: a dictionary which contains one key: MIB
            @rtype: dictionary
            """
            result = {}
            try:
                exec pythonCode in result
            except Exception:
                self.log.exception("Unable to import Pythonized-MIB: %s",
                    name)
            return result.get('MIB', None)

        # If more than one MIB definition exists in a file, pythonCode will
        # contain a 'MIB = {...}' section for each MIB definition. We must
        # split each section into its own string and return a string list.
        smiMibDelim = 'MIB = {'
        mibCodeParts = pythonCode.split(smiMibDelim)
        mibDicts = []
        # Check for a TRAP-TYPE in the mib file, since smidump parse it with
        # extra zero in Trap OID
        if "TRAP-TYPE" in pythonCode and not self.options.removemiddlezeros:
            self.log.warn("This MIB file contains a type of OID (TRAP-TYPE) "
                          "that, when parsed, inserts an extra zero into "
                          "the OID causing SNMP trap lookups to fail. "
                          "Please run zenmib with the '--removemiddlezeros' "
                          "flag option to avoid this problem.")
        if len(mibCodeParts) > 1:
            for mibCodePart in mibCodeParts[1:]:
                mibDict = executePythonCode(smiMibDelim + mibCodePart, name)
                if mibDict is not None:
                    mibDicts.append(mibDict)
        else:
            mibDict = executePythonCode(pythonCode, name)
            if mibDict is not None:
                mibDicts = [mibDict]

        return mibDicts

    def evalAddSavedPythonCode(self):
        """
        Read the file named in the command-line option, evaluate it, and add
        it to our list of MIBs.
        """
        pythonMibs = []
        for fileName in set(self.options.evalSavedPython):
            try:
                pythonCode = open(fileName).read()
            except IOError:
                self.log.warn("Unable to open '%s' -- skipping", 
                              fileName)
                continue
            pythonMibs += self.evalPythonToMibs(pythonCode, fileName)

        self.loadPythonMibs(pythonMibs)


    def getDmdMibDict(self, dmdMibDict, mibOrganizer):
        """
        Populate a dictionary containing the MIB definitions that have been
        loaded into the DMD Mibs directory

        @param dmdMibDict: maps a MIB definition to the path where
                it is located with in the DMD.
            Format:
                {'mibName': 'DMD path where mibName is stored'}
            Example: MIB-Dell-10892 is located in the DMD tree at
                Mibs/SITE/Dell, Directory entry is
                {'MIB-Dell-10892': '/SITE/Dell'] }
        @param mibOrganizer: the DMD directory to be searched
        @type mibOrganizer: MibOrganizer
        """
        organizerPath = mibOrganizer.getOrganizerName()

        # Record each module from this organizer as a dictionary entry.
        # mibOrganizer.mibs.objectItems() returns tuple:
        # ('mibName', <MibModule at /zport/dmd/Mibs/...>)
        for mibModule in mibOrganizer.mibs.objectItems():
            mibName = mibModule[0]
            if mibName not in dmdMibDict:
                dmdMibDict[mibName] = organizerPath
            else:
                self.log.warn('\nFound two copies of %s:'
                    '  %s and %s' %
                    (mibName, dmdMibDict[mibName],
                    mibOrganizer.getOrganizerName()))

        # If there are suborganizers, recurse into them
        for childOrganizer in mibOrganizer.children():
            self.getDmdMibDict(dmdMibDict, childOrganizer)

    def addMibEntries(self, leafType, pythonMib, mibModule):
        """
        Add the different MIB leaves (ie nodes, notifications) into the DMD.

        @paramater leafType: 'nodes', 'notifications'
        @type leafType: string
        @paramater pythonMib: dictionary of nodes and notifications
        @type pythonMib: dictionary
        @paramater mibModule: class containing functions to load leaves
        @type mibModule: class
        @return: number of leaves added
        @rtype: int
        """
        entriesAdded = 0
        functor = { 'nodes':mibModule.createMibNode,
                    'notifications':mibModule.createMibNotification,
                   }.get(leafType, None)
        if not functor or leafType not in pythonMib:
            return entriesAdded

        mibName = pythonMib['moduleName']

        for name, values in pythonMib[leafType].items():

            if self.options.removemiddlezeros:
                # smidump add zeros according to SMIv2
                oid = values['oid']
                if '.0.' in oid:
                    values['oid'] = oid.replace('.0.', '.')
                    self.log.warn("Found a zero index in OID"
                                  " '%s' -- converting to '%s'",
                                  oid, values['oid'])
            
            try:
                functor(name, logger=self.log, **values)
                entriesAdded += 1
            except BadRequest:
                try:
                    self.log.warn("Unable to add %s id '%s' as this"
                                " name is reserved for use by Zope",
                                leafType, name)
                    newName = '_'.join([name, mibName])
                    self.log.warn("Trying to add %s '%s' as '%s'",
                                leafType, name, newName)
                    functor(newName, **values)
                    entriesAdded += 1
                    self.log.warn("Renamed '%s' to '%s' and added to"
                                " MIB %s", name, newName, leafType)
                except Exception:
                    self.log.warn("Unable to add %s id '%s' -- skipping",
                                leafType, name)
            else:
                if not entriesAdded % CHUNK_SIZE:
                    self.commit("Loaded MIB %s into the DMD" % mibName)
        self.commit("Loaded MIB %s into the DMD" % mibName)
        return entriesAdded

    def loadMibFile(self, mibFileObj, dmdMibDict):
        """
        Attempt to load the MIB definitions in fileName into DMD

        @param fileName: name of the MIB file to be loaded
        @type fileName: string
        @return: whether the MIB load was successful or not
        @rtype: boolean
        """
        fileName = mibFileObj.fileName
        self.log.debug('Attempting to load %s' % fileName)

        mibNamesInFile = mibFileObj.mibs
        # Retrieve a list of all the files containing MIB definitions that are
        # required by the MIB definitions in fileName
        dependencyFileNames = self.getDependencyFileNames(mibFileObj)

        # Convert the MIB file data into python dictionaries. pythonMibs
        # contains a list of dictionaries, one for each MIB definition in
        # fileName.
        pythonMibs = self.generatePythonFromMib(fileName, dependencyFileNames,
            mibNamesInFile)
        if not pythonMibs:
            return False

        self.loadPythonMibs(pythonMibs, dmdMibDict)
        return True

    def commit(self, message):
        if not self.options.nocommit:
            self.log.debug('Committing a batch of objects')
            trans = transaction.get()
            trans.setUser('zenmib')
            trans.note(message)
            trans.commit()
            self.syncdb()

    def loadPythonMibs(self, pythonMibs, dmdMibDict=None):
        """
        Walk through the MIB dictionaries and add the MIBs to the DMD.
        """
        # Standard MIB attributes that we expect in all MIBs
        MIB_MOD_ATTS = ('language', 'contact', 'description')

        self.syncdb()

        # Add the MIB data for each MIB into Zenoss
        for pythonMib in pythonMibs:
            mibName = pythonMib['moduleName']

            # Check to see if any MIB definitions in fileName have already 
            # been loaded into Zenoss. If so, warn but don't fail 
            dmdMibPath=self.options.path 
            if dmdMibDict is not None and mibName in dmdMibDict: 
                dmdMibPath = dmdMibDict[mibName] 
                self.log.warn('MIB definition %s is already ' 
                    'loaded at %s. Will update it.' % (mibName, dmdMibPath)) 
                mibModule = self.dmd.Mibs.mibs.findObjectsById(mibName)[0] 

            # Create the container for the MIBs and define meta-data.
            # In the DMD this creates another container class which
            # contains mibnodes.  These data types are found in
            # Products.ZenModel.MibModule and Products.ZenModel.MibNode
            else:
                mibModule = self.dmd.Mibs.createMibModule(
                    mibName, dmdMibPath)

            def gen():
                for key, val in pythonMib[mibName].iteritems():
                    if key in MIB_MOD_ATTS:
                        yield key, val

            for i, attr in enumerate(gen()):
                setattr(mibModule, *attr)
                if not i % CHUNK_SIZE:
                    self.commit("Loaded MIB %s into the DMD" % mibName)
            self.commit("Loaded MIB %s into the DMD" % mibName)

            nodesAdded = self.addMibEntries('nodes', pythonMib, mibModule)
            trapsAdded = self.addMibEntries('notifications', pythonMib, mibModule)
            self.log.info("Parsed %d nodes and %d notifications from %s",
                          nodesAdded, trapsAdded, mibName)

            # Add the MIB tree permanently to the DMD unless --nocommit flag.
            msg = "Loaded MIB %s into the DMD" % mibName
            self.commit(msg)
            if not self.options.nocommit:
                self.log.info(msg)


    def getAllMibDepFileNames(self):
        """
        Use command line parameters to create a list of files containing MIB
        definitions that will be used as a reference list for the files being
        loaded into the DMD

        @return: set of file names
        @rtype: set
        """
        defaultMibDepDirs = [ 'ietf', 'iana', 'irtf', 'tubs', 'site' ]
        mibDepFileNames = set()
        mibDepFileNames.update(self.pkgMgr.processDir(self.options.mibdepsdir))
        for subdir in defaultMibDepDirs:
            depDir = os.path.join(self.options.mibdepsdir, subdir)
            mibDepFileNames.update(self.pkgMgr.processDir(depDir))
        return mibDepFileNames

    def getMibsToImport(self):
        """
        Uses command-line parameters to create a list of files containing MIB
        definitions that are to be loaded into the DMD

        @return: list of file names that are to be loaded into the DMD
        @rtype: list
        """
        loadFileNames = []
        if self.args:
            for fileName in self.args:
                loadFileNames.extend(self.pkgMgr.downloadExtract(fileName))
        else:
            loadFileNames = self.pkgMgr.processDir(self.options.mibsdir)

        if loadFileNames:
            self.log.debug("Will attempt to load the following files: %s",
                       loadFileNames)
        else:
            self.log.error("No MIB files to load!")
            sys.exit(1)

        return set(loadFileNames)

    def main(self):
        """
        Main loop of the program
        """
        if self.options.evalSavedPython:
            self.evalAddSavedPythonCode()
            return

        # Verify MIBs search directory is valid. Fail if not
        if not os.path.exists(self.options.mibsdir):
            self.log.error("The directory %s doesn't exist!" %
                self.options.mibsdir )
            sys.exit(1)

        self.pkgMgr = PackageManager(self.log, self.options.downloaddir,
                                     self.options.extractdir)
        self.mibToMibFile = {}

        requestedFiles = self.getMibsToImport()
        mibDepFileNames = self.getAllMibDepFileNames()
        mibFileObjs = self.populateDependencyMap(requestedFiles, mibDepFileNames)

        # dmdMibDict = {'mibName': 'DMD path to MIB'}
        dmdMibDict = {}
        self.getDmdMibDict(dmdMibDict, self.dmd.Mibs)

        # Load the MIB files
        self.log.info("Found %d MIBs to import.", len(mibFileObjs))
        loadedMibFiles = 0
        for mibFileObj in mibFileObjs:
            try:
                if self.loadMibFile(mibFileObj, dmdMibDict):
                    loadedMibFiles += 1
            except Exception:
                self.log.exception("Failed to load MIB: %s", mibFileObj.fileName)

        action = "Loaded"
        if self.options.nocommit:
            action = "Processed"

        self.log.info("%s %d MIB file(s)" % (action, loadedMibFiles))
        self.pkgMgr.cleanup()

        sys.exit(0)

    def buildOptions(self):
        """
        Command-line options
        """
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--mibsdir',
                               dest='mibsdir', default=zenPath('share/mibs/site'),
                       help="Directory of input MIB files [ default: %default ]")
        self.parser.add_option('--mibdepsdir',
                        dest='mibdepsdir', default=zenPath('share/mibs'),
                       help="Directory of input MIB files [ default: %default ]")
        self.parser.add_option('--path',
                               dest='path', default="/",
                               help="Path to load MIB into the DMD")
        self.parser.add_option('--nocommit', action='store_true',
                               dest='nocommit', default=False,
                           help="Don't commit the MIB to the DMD after loading")
        self.parser.add_option('--keeppythoncode', action='store_true',
                               dest='keeppythoncode', default=False,
                           help="Don't commit the MIB to the DMD after loading")
        self.parser.add_option('--pythoncodedir', dest='pythoncodedir',
            default=tempfile.gettempdir() + "/mib_pythoncode/",
            help="This is the directory where the converted MIB will be output. " \
                "[ default: %default ]")
        self.parser.add_option('--downloaddir', dest='downloaddir',
            default=tempfile.gettempdir() + "/mib_downloads/",
            help="This is the directory where the MIB will be downloaded. " \
                "[ default: %default ]")
        self.parser.add_option('--extractdir', dest='extractdir',
            default=tempfile.gettempdir() + "/mib_extract/",
            help="This is the directory where unzipped MIB files will be stored. " \
                "[ default: %default ]")
        self.parser.add_option('--evalSavedPython', dest='evalSavedPython',
                           default=[], action='append',
                           help="Execute the Python code previously generated" \
                                " and saved.")
        self.parser.add_option('--removemiddlezeros', dest='removemiddlezeros',
                            default=False, action='store_true',
                            help="Remove zeros found in the middle of the oid.")


if __name__ == '__main__':
    zm = ZenMib()
    zm.main()
