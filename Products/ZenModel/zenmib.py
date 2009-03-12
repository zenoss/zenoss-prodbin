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
__doc__= """zenmib
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
import glob
import re
from subprocess import Popen, PIPE

import Globals
import transaction

from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.Utils import zenPath
from zExceptions import BadRequest


def walk(*dirs):
    """
    Generator function to create a list of absolute paths
    for all files in a directory tree starting from the list
    of directories given as arguments to this function.

    @param *dirs: list of directories to investigate
    @type *dirs: list of strings
    @return: directory to investigate
    @rtype: string
    """
    for dir in dirs:
        for dirname, _, filenames in os.walk(dir):
            for filename in filenames:
                yield os.path.join(dirname, filename)



class DependencyMap:
    """
    A dependency is a reference to another part of the MIB tree.
    All MIB definitions start from the base of the tree (ie .1).
    Generally dependencies are from MIB definitions external to
    the MIB under inspection.
    """

    def __init__(self):
        self.fileMap = {}
        self.depMap = {}


    def add(self, filename, name, dependencies):
        """
        Add a dependency to the dependency tree if it's not already there.

        @param filename: name of MIB file to import
        @type filename: string
        @param name: name of MIB
        @type name: string
        @param dependencies: dependency
        @type dependencies: dependency object
        """
        if not self.depMap.has_key(name):
            self.fileMap[filename] = name
            self.depMap[name] = (filename, dependencies)


    def getName(self, filename):
        """
        Given a filename, return the name of the MIB tree defined in it.
        Makes the assumption that there's only one MIB tree per file.

        @param filename: MIB filename
        @type filename: string
        @return: MIB name
        @rtype: string
        @todo: to allow for multiple MIBs in a file, should return a list
        """
        return self.fileMap.get(filename, None)


    def getDependencies(self, name):
        """
        Given a name of the MIB tree, return the filename that it's from
        and its dependencies.

        @param name: name of MIB
        @type name: string
        @return: dependency tree
        @rtype: tuple of ( name, dependency object)
        """
        return self.depMap.get(name, None)



class zenmib(ZCmdBase):
    """
    Wrapper around the smidump utilities to load MIB files into
    the DMD tree.
    """

    def map_file_to_dependents(self, mibfile):
        """
        Scan the MIB file to determine what MIB trees the file is dependent on.

        @param mibfile: MIB filename
        @type mibfile: string
        @return: dependency tree
        @rtype: tuple of ( name, dependency object)
        """
        # Slurp in the whole file
        fp = open(mibfile)
        mib = fp.read()
        fp.close()

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
        #     -- contact IANA for actual number
        # 
        # root    OBJECT IDENTIFIER ::= { experimental xx }
        # 
        # END

        DEFINITIONS = re.compile(r'(?P<mib_name>[A-Za-z-0-9]+) +DEFINITIONS *::= *BEGIN')
        DEPENDS = re.compile(r'FROM *(?P<mib_dependency>[A-Za-z-0-9]+)')

        # Split up the file and determine what OIDs need what other OIDs
        #
        # TODO: Fix the code so that it takes care of the case where there are multiple
        #       OBJECT IDENTIFIER sections in the MIB.
        parts = mib.split('OBJECT IDENTIFIER', 1)
        mib_prologue = parts[0]
        match = DEFINITIONS.search(mib_prologue)
        if not match:
             # Special case: bootstrap MIB for the root of the MIB tree
             return None, []

        # Search through the prologue to find all of the IMPORTS.
        # An example from a real MIB
        #
        # IMPORTS
        #        MODULE-IDENTITY, OBJECT-TYPE,  enterprises, Integer32,
        #        TimeTicks,NOTIFICATION-TYPE             FROM SNMPv2-SMI
        #        DisplayString                           FROM RFC1213-MIB
        #        MODULE-COMPLIANCE, OBJECT-GROUP,
        #        NOTIFICATION-GROUP                      FROM SNMPv2-CONF;
        depends = []
        name = match.group('mib_name')
        start = match.end(0)  # Jump to past the first FROM token
        while 1:
            match = DEPENDS.search(mib_prologue, start)
            if not match:
                break

            depends.append(match.group('mib_dependency'))

            # Skip to just past the next FROM token
            start = match.end(0)

        return name, depends
        


    def dependencies(self, filenames):
        """
        Create a dependency map for all MIB files.
        Exit the program if we're missing any files.

        @param filenames: names of MIB files to import
        @type filenames: list of strings
        @return: dependency tree
        @rtype: DependencyMap
        """
        missing_files = 0
        result = DependencyMap()
        for filename in filenames:
            try:
                defines, depends = self.map_file_to_dependents(filename)

            except IOError:
                self.log.error( "Couldn't open file %s", filename)
                missing_files += 1
                continue

            if defines == None:
                self.log.debug( "Unable to parse information from %s -- skipping", filename)
            else:
                result.add(filename, defines, depends)

        if missing_files > 0:
            self.log.error( "Missing %s files", missing_files )
            sys.exit(1)

        return result



    def getDependencies(self, filename, depMap):
        """
        smidump needs to know the list of dependent files for a MIB file in
        order to properly resolve external references.

        @param filename: name of MIB file to import
        @type filename: string
        @param depMap: dependency tree
        @type depMap: DependencyMap
        @return: list of dependencies
        @rtype: list of strings
        """
        # Sanity check: if a file doesn't need anything else, it
        # has no dependencies.  Avoid further work.
        name = depMap.getName(filename)
        if not name:
            return []

        # Find the files required by the OID tree in the file.
        deps = []
        def dependency_search(name):
            """
            Create a list of files required by an OID.

            @param name: name of OID
            @type name: string
            """
            fileAndDeps = depMap.getDependencies(name)
            if not fileAndDeps:
                self.log.warn( "Unable to find a file providing the OID %s", name)
                return

            mib_file, dependent_oids = fileAndDeps
            if mib_file and mib_file not in deps:
                deps.append(mib_file)

            for unresolved_oid in dependent_oids:
                dependency_search(unresolved_oid)

        # Search the dependency map
        dependency_search(name)
        if deps[1:]:
            return deps[1:]

        return []


    
    def generate_python_from_mib( self, mibname, dependencies ):
        """
        Use the smidump program to convert a MIB into Python code"

        @param mibname: name of the MIB
        @type mibname: string
        @param dependencies: list of dependent files
        @type dependencies: list of strings
        @return: the newly created MIB
        @rtype: MIB object
        """
        dump_command =  [ 'smidump', '-k', '-fpython' ]
        for dep in dependencies[1:]:
            #  Add command-line flag for our dependent files
            dump_command.append( '-p')
            dump_command.append( dep )

        dump_command.append( mibname )
        self.log.debug('Running %s', ' '.join( dump_command))
        proc = Popen( dump_command, stdout=PIPE, stderr=PIPE )

        python_code, warnings = proc.communicate()
        proc.wait()
        if proc.returncode:
            self.log.error(warnings)
            return None

        if len(warnings) > 0:
            self.log.debug("Found warnings while trying to import MIB:\n%s" \
                 % warnings)

        # Now we'll be brave and try to execute the MIB-to-python code
        # and store the resulting dictionary in 'result'
        result = {}
        try:
            exec python_code in result

        except (SystemExit, KeyboardInterrupt): raise
        except:
            self.log.exception("Unable to import Pythonized-MIB: %s", mibname)
            return None

        # Now look for the start of the MIB
        mib = result.get( 'MIB', None)
        return mib



    # Standard MIB attributes that we expect in all MIBs
    MIB_MOD_ATTS = ('language', 'contact', 'description')

    def load_mib(self, mibs, mibname, depmap):
        """
        Attempt to load a MIB after generating its dependency tree

        @param mibs: filenames of the MIBs to load
        @type mibs: list of strings
        @param mibname: name of the MIB
        @type mibname: string
        @param dependencies: list of dependent files
        @type dependencies: string
        @return: whether the MIB load was successful or not
        @rtype: boolean
        """
        dependencies = self.getDependencies(mibname, depmap)

        mib = self.generate_python_from_mib( mibname, dependencies )
        if not mib:
            return False

        # Check for duplicates -- or maybe not...
        modname = mib['moduleName']
        # TODO: Find out Why this is commented out
        #mod = mibs.findMibModule(modname)
        mod = None
        if mod:
            self.log.warn( "Skipping %s as it is already loaded", modname)
            return False

        # Create the container for the MIBs and define meta-data
        # In the DMD this creates another container class which
        # contains mibnodes.  These data types are found in
        # Products.ZenModel.MibModule and Products.ZenModel.MibNode
        mod = mibs.createMibModule(modname, self.options.path)
        for key, val in mib[modname].items():
            if key in self.MIB_MOD_ATTS:
                setattr(mod, key, val)

        # Add regular OIDs to the mibmodule + mibnode relationship tree
        if mib.has_key('nodes'):
            for name, values in mib['nodes'].items():
                try:
                    mod.createMibNode(name, **values)
                except BadRequest:
                    try:
                        self.log.warn("Unable to add node id '%s' as this"
                                      " name is reserved for use by Zope",
                                      name)
                        newName = '_'.join([name, modname])
                        self.log.warn("Trying to add node '%s' as '%s'",
                                  name, newName)
                        mod.createMibNode(newName, **values)
                        self.log.warn("Renamed '%s' to '%s' and added to MIB"
                                  " nodes", name, newName)
                    except:
                        self.log.warn("Unable to add '%s' -- skipping",
                                      name)

        # Put SNMP trap information into Products.ZenModel.MibNotification
        if mib.has_key('notifications'):
            for name, values in mib['notifications'].items():
                try:
                    mod.createMibNotification(name, **values)
                except BadRequest:
                    try:
                        self.log.warn("Unable to add trap id '%s' as this"
                                      " name is reserved for use by Zope",
                                      name)
                        newName = '_'.join([name, modname])
                        self.log.warn("Trying to add trap '%s' as '%s'",
                                  name, newName)
                        mod.createMibNotification(newName, **values)
                        self.log.warn("Renamed '%s' to '%s' and added to MIB"
                                  " traps", name, newName)
                    except:
                        self.log.warn("Unable to add '%s' -- skipping",
                                      name)

        # Add the MIB tree permanently to the DMD except if we get the
        # --nocommit flag.
        if not self.options.nocommit:
            trans = transaction.get()
            trans.setUser( "zenmib" ) 
            trans.note("Loaded MIB %s into the DMD" % modname)
            trans.commit() 
            self.log.info("Loaded MIB %s into the DMD", modname)

        return True



    def main(self):
        """
        Main loop of the program
        """
        # Prepare to load the default MIBs
        smimibdir = self.options.mibsdir
        if not os.path.exists( smimibdir ):
            self.log.error("The directory %s doesn't exist!" % smimibdir )
            sys.exit(1)

        ietf, iana, irtf, tubs, site = \
              map(lambda x: os.path.join(smimibdir, x),
                  'ietf iana irtf tubs site'.split())

        # Either load MIBs from the command-line or from the default
        # location where MIBs are stored by Zenoss.
        if len(self.args) > 0:
            mibnames = self.args
            depMap = self.dependencies(list(walk(ietf, iana, irtf, tubs))
                                       + mibnames)
        else:
            mibnames = glob.glob(os.path.join(smimibdir, 'site', '*'))
            depMap = self.dependencies(walk(ietf, iana, irtf, tubs, site))

        # Make connection to the DMD at the start of the MIB tree
        mibs = self.dmd.Mibs

        # Process all of the MIBs that we've found
        loaded_mib_files = 0
        for mibname in mibnames:
            try:
                if self.load_mib( mibs, mibname, depMap):
                    loaded_mib_files += 1

            except (SystemExit, KeyboardInterrupt): raise
            except Exception, ex:
                self.log.exception("Failed to load MIB: %s" % mibname)

        action = "Loaded"
        if self.options.nocommit:
            action = "Processed"
        self.log.info( "%s %d MIB file(s)" % ( action, loaded_mib_files))
        sys.exit(0)

        
    def buildOptions(self):
        """
        Command-line options
        """
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--mibsdir', 
                               dest='mibsdir', default=zenPath('share/mibs'),
                               help="Directory of input MIB files [ default: %default ]")
        self.parser.add_option('--path', 
                               dest='path', default="/",
                               help="Path to load MIB into the DMD")
        self.parser.add_option('--nocommit', action='store_true',
                               dest='nocommit', default=False,
                               help="Don't commit the MIB to the DMD after loading")


if __name__ == '__main__':
    zm = zenmib()
    zm.main()
