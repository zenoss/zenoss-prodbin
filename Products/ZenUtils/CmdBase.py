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

__doc__="""CmdBase

Provide utility functions for logging and config file parsing
to command-line programs
"""

import os
import sys
import datetime
import logging

import zope.component
from zope.traversing.adapters import DefaultTraversable
from Products.Five import zcml

from logging import handlers
from optparse import OptionParser, SUPPRESS_HELP, NO_DEFAULT
from urllib import quote

# There is a nasty incompatibility between pkg_resources and twisted.
# This pkg_resources import works around the problem.
# See http://dev.zenoss.org/trac/ticket/3146 for details
from Products.ZenUtils.PkgResources import pkg_resources

from Products.ZenUtils.Utils import unused
unused(pkg_resources)

class DMDError: pass

class CmdBase(object):
    """
    Class used for all Zenoss commands
    """

    doesLogging = True

    def __init__(self, noopts=0):

        # We must import ZenossStartup at this point so that all Zenoss daemons
        # and tools will have any ZenPack monkey-patched methods available.
        zope.component.provideAdapter(DefaultTraversable, (None,))
        import Products.Five, Products.ZenModel, Products.ZenRelations
        import Products.ZenWidgets, Products.Zuul
        try:
            zcml.load_config('meta.zcml', Products.Five)
            zcml.load_config('indexing.zcml', Products.ZenModel)
            zcml.load_config('zendoc.zcml', Products.ZenModel)
            zcml.load_config('configure.zcml', Products.ZenRelations)
            zcml.load_config('configure.zcml', Products.Zuul)
            zcml.load_config('scriptmessaging.zcml', Products.ZenWidgets)
        except AttributeError:
            # Could be that we're in a pre-Product-installation Zope, e.g. in
            # zenwipe. No problem, we won't need this stuff now anyway.
            pass
        import Products.ZenossStartup
        unused(Products.ZenossStartup)

        self.usage = "%prog [options]"
        self.noopts = noopts
        self.args = []
        self.parser = None
        self.buildParser()
        self.buildOptions()
        
        self.parseOptions()
        if self.options.configfile:
            self.getConfigFileDefaults( self.options.configfile )

            # We've updated the parser with defaults from configs, now we need
            # to reparse our command-line to get the correct overrides from
            # the command-line
            self.parseOptions()
        if self.doesLogging:
            self.setupLogging()


    def getConfigFileDefaults(self, filename):
        """
        Parse a config file which has key-value pairs delimited by white space,
        and update the parser's option defaults with these values.

        @parameter filename: name of configuration file
        @type filename: string
        """
        outlines = []
        
        try:
            configFile = open(filename)
            lines = configFile.readlines()
            configFile.close()
        except:
            import traceback
            print >>sys.stderr, "WARN: unable to read config file %s -- skipping" % \
                   filename
            traceback.print_exc(0)
            return
        
        lineno = 0
        modified = False
        for line in lines:
            outlines.append(line)
            lineno += 1
            if line.lstrip().startswith('#'): continue
            if line.strip() == '': continue

            try:
                key, value = line.strip().split(None, 1)
            except ValueError:
                print >>sys.stderr, "WARN: missing value on line %d" % lineno
                continue
            flag= "--%s" % key
            option= self.parser.get_option( flag )
            if option is None:
                print >>sys.stderr, "INFO: Commenting out unknown option '%s' found " \
                                    "on line %d in config file" % (key, lineno)
                #take the last line off the buffer and comment it out
                outlines = outlines[:-1]
                outlines.append('## %s' % line)
                modified = True
                continue
            
            # NB: At this stage, optparse accepts even bogus values
            #     It will report unhappiness when it parses the arguments
            try:
                if option.action in [ "store_true", "store_false" ]:
                    if value in ['True', 'true']:
                        value = True
                    else:
                        value = False
                    self.parser.set_default( option.dest, value )
                else:
                    self.parser.set_default( option.dest, type(option.type)(value) )
            except:
                print >>sys.stderr, "Bad configuration value for" \
                    " %s at line %s, value = %s (type %s)" % (
                    option.dest, lineno, value, option.type )
        
        #if we found bogus options write out the file with commented out bogus 
        #values
        if modified:
            configFile = file(filename, 'w')
            configFile.writelines(outlines)
            configFile.close()

    def checkLogpath(self):
        """
        Validate the logpath is valid
        """
        if not self.options.logpath:
            return None
        else:
            logdir = self.options.logpath
            if not os.path.exists(logdir):
                # try creating the directory hierarchy if it doesn't exist...
                try:
                    os.makedirs(logdir)
                except OSError, ex:
                    raise SystemExit("logpath:%s doesn't exist and cannot be created" % logdir)
            elif not os.path.isdir(logdir):
                raise SystemExit("logpath:%s exists but is not a directory" % logdir)
            return logdir

    def setupLogging(self):
        """
        Set common logging options
        """
        rlog = logging.getLogger()
        rlog.setLevel(logging.WARN)
        mname = self.__class__.__name__
        self.log = logging.getLogger("zen."+ mname)
        zlog = logging.getLogger("zen")
        zlog.setLevel(self.options.logseverity)
        logdir = self.checkLogpath()
        if logdir:
            logfile = os.path.join(logdir, mname.lower()+".log")
            maxBytes = self.options.maxLogKiloBytes * 1024
            backupCount = self.options.maxBackupLogs
            h = logging.handlers.RotatingFileHandler(logfile, maxBytes, backupCount)
            h.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s",
                "%Y-%m-%d %H:%M:%S"))
            rlog.addHandler(h)
        else:
            logging.basicConfig()


    def buildParser(self):
        """
        Create the options parser
        """
        if not self.parser:
            from Products.ZenModel.ZenossInfo import ZenossInfo
            try:
                zinfo= ZenossInfo('')
                version= str(zinfo.getZenossVersion())
            except:
                from Products.ZenModel.ZVersion import VERSION
                version= VERSION
            self.parser = OptionParser(usage=self.usage, 
                                       version="%prog " + version )

    def buildOptions(self):
        """
        Basic options setup. Other classes should call this before adding
        more options
        """
        self.buildParser()
        if self.doesLogging:
            self.parser.add_option('-v', '--logseverity',
                        dest='logseverity',
                        default=20,
                        type='int',
                        help='Logging severity threshold')

            self.parser.add_option('--logpath',dest='logpath',
                        help='Override the default logging path')
            
            self.parser.add_option('--maxlogsize',
                        dest='maxLogKiloBytes',
                        help='Max size of log file in KB; default 10240',
                        default=10240,
                        type='int')
            
            self.parser.add_option('--maxbackuplogs',
                        dest='maxBackupLogs',
                        help='Max number of back up log files; default 3',
                        default=3,
                        type='int')

        self.parser.add_option("-C", "--configfile", 
                    dest="configfile",
                    help="Use an alternate configuration file" )

        self.parser.add_option("--genconf",
                               action="store_true",
                               default=False,
                               help="Generate a template configuration file" )

        self.parser.add_option("--genxmltable",
                               action="store_true",
                               default=False,
                               help="Generate a Docbook table showing command-line switches." )

        self.parser.add_option("--genxmlconfigs",
                               action="store_true",
                               default=False,
                               help="Generate an XML file containing command-line switches." )




    def pretty_print_config_comment( self, comment ):
        """
        Quick and dirty pretty printer for comments that happen to be longer than can comfortably
be seen on the display.
        """

        max_size= 40
        #
        # As a heuristic we'll accept strings that are +-  text_window
        # size in length. 
        #
        text_window= 5

        if len( comment ) <= max_size + text_window:
             return comment

        #
        # First, take care of embedded newlines and expand them out to array entries
        #
        new_comment= []
        all_lines= comment.split( '\n' )
        for line in all_lines:
           if len(line) <= max_size + text_window:
                new_comment.append( line )
                continue

           start_position= max_size - text_window
           while len(line) > max_size + text_window:
                index= line.find( ' ', start_position )
                if index > 0:
                     new_comment.append( line[ 0:index ] )
                     line= line[ index: ]

                else:
                     if start_position == 0:
                        #
                        # If we get here it means that the line is just one big string with no spaces
                        # in it.  There's nothing that we can do except print it out.  Doh!
                        #
                        new_comment.append( line )
                        break

                     #
                     # Okay, haven't found anything to split on -- go back and try again
                     #
                     start_position= start_position - text_window
                     if start_position < 0:
                        start_position= 0

           else:
                new_comment.append( line )

        return "\n# ".join( new_comment )



    def generate_configs( self, parser, options ):
        """
        Create a configuration file based on the long-form of the option names

        @parameter parser: an optparse parser object which contains defaults, help
        @parameter options: parsed options list containing actual values
        """

        #
        # Header for the configuration file
        #
        unused(options)
        daemon_name= os.path.basename( sys.argv[0] )
        daemon_name= daemon_name.replace( '.py', '' )

        print """#
# Configuration file for %s
#
#  To enable a particular option, uncomment the desired entry.
#
# Parameter     Setting
# ---------     -------""" % ( daemon_name )


        options_to_ignore= ( 'help', 'version', '', 'genconf', 'genxmltable' )

        #
        # Create an entry for each of the command line flags
        #
        # NB: Ideally, this should print out only the option parser dest
        #     entries, rather than the command line options.
        #
        import re
        for opt in parser.option_list:
                if opt.help is SUPPRESS_HELP:
                        continue

                #
                # Get rid of the short version of the command
                #
                option_name= re.sub( r'.*/--', '', "%s" % opt )

                #
                # And what if there's no short version?
                #
                option_name= re.sub( r'^--', '', "%s" % option_name )

                #
                # Don't display anything we shouldn't be displaying
                #
                if option_name in options_to_ignore:
                        continue

                #
                # Find the actual value specified on the command line, if any, 
                # and display it
                #
                
                value= getattr( parser.values,  opt.dest )

                default_value= parser.defaults.get( opt.dest )
                if default_value is NO_DEFAULT or default_value is None:
                        default_value= ""
                default_string= ""
                if default_value != "":
                        default_string= ", default: " + str( default_value )

                comment=  self.pretty_print_config_comment( opt.help + default_string )

                #
                # NB: I would prefer to use tabs to separate the parameter name
                #     and value, but I don't know that this would work.
                #
                print """#
# %s
#%s %s""" % ( comment, option_name, value )

        #
        # Pretty print and exit
        #
        print "#"
        sys.exit( 0 )



    def generate_xml_table( self, parser, options ):
        """
        Create a Docbook table based on the long-form of the option names

        @parameter parser: an optparse parser object which contains defaults, help
        @parameter options: parsed options list containing actual values
        """

        #
        # Header for the configuration file
        #
        unused(options)
        daemon_name= os.path.basename( sys.argv[0] )
        daemon_name= daemon_name.replace( '.py', '' )

        print """<?xml version="1.0" encoding="UTF-8"?>

<section version="4.0" xmlns="http://docbook.org/ns/docbook"
   xmlns:xlink="http://www.w3.org/1999/xlink"
   xmlns:xi="http://www.w3.org/2001/XInclude"
   xmlns:svg="http://www.w3.org/2000/svg"
   xmlns:mml="http://www.w3.org/1998/Math/MathML"
   xmlns:html="http://www.w3.org/1999/xhtml"
   xmlns:db="http://docbook.org/ns/docbook"

  xml:id="%s.options"
>

<title>%s Options</title>
<para />
<table frame="all">
  <caption>%s <indexterm><primary>Daemons</primary><secondary>%s</secondary></indexterm> options</caption>
<tgroup cols="2">
<colspec colname="option" colwidth="1*" />
<colspec colname="description" colwidth="2*" />
<thead>
<row>
<entry> <para>Option</para> </entry>
<entry> <para>Description</para> </entry>
</row>
</thead>
<tbody>
""" % ( daemon_name, daemon_name, daemon_name, daemon_name )


        options_to_ignore= ( 'help', 'version', '', 'genconf', 'genxmltable' )

        #
        # Create an entry for each of the command line flags
        #
        # NB: Ideally, this should print out only the option parser dest
        #     entries, rather than the command line options.
        #
        import re
        for opt in parser.option_list:
                if opt.help is SUPPRESS_HELP:
                        continue

                #
                # Create a Docbook-happy version of the option strings
                # Yes, <arg></arg> would be better semantically, but the output
                # just looks goofy in a table.  Use literal instead.
                #
                all_options= '<literal>' + re.sub( r'/', '</literal>,</para> <para><literal>', "%s" % opt ) + '</literal>'

                #
                # Don't display anything we shouldn't be displaying
                #
                option_name= re.sub( r'.*/--', '', "%s" % opt )
                option_name= re.sub( r'^--', '', "%s" % option_name )
                if option_name in options_to_ignore:
                        continue

                default_value= parser.defaults.get( opt.dest )
                if default_value is NO_DEFAULT or default_value is None:
                        default_value= ""
                default_string= ""
                if default_value != "":
                        default_string= "<para> Default: <literal>" + str( default_value ) + "</literal></para>\n"

                comment= self.pretty_print_config_comment( opt.help )

#
# TODO: Determine the variable name used and display the --option_name=variable_name
#
                if opt.action in [ 'store_true', 'store_false' ]:
                   print """<row>
<entry> <para>%s</para> </entry>
<entry>
<para>%s</para>
%s</entry>
</row>
""" % ( all_options, comment, default_string )

                else:
                   target= '=<replaceable>' +  opt.dest.lower() + '</replaceable>'
                   all_options= all_options + target
                   all_options= re.sub( r',', target + ',', all_options )
                   print """<row>
<entry> <para>%s</para> </entry>
<entry>
<para>%s</para>
%s</entry>
</row>
""" % ( all_options, comment, default_string )



        #
        # Close the table elements
        #
        print """</tbody></tgroup>
</table>
<para />
</section>
"""
        sys.exit( 0 )



    def generate_xml_configs( self, parser, options ):
        """
        Create an XML file that can be used to create Docbook files
        as well as used as the basis for GUI-based daemon option
        configuration.
        """

        #
        # Header for the configuration file
        #
        unused(options)
        daemon_name= os.path.basename( sys.argv[0] )
        daemon_name= daemon_name.replace( '.py', '' )

        export_date = datetime.datetime.now()

        print """<?xml version="1.0" encoding="UTF-8"?>

<!-- Default daemon configuration generated on %s -->
<configuration id="%s" >

""" % ( export_date, daemon_name )

        options_to_ignore= ( 
            'help', 'version', '', 'genconf', 'genxmltable',
            'genxmlconfigs',
        )

        #
        # Create an entry for each of the command line flags
        #
        # NB: Ideally, this should print out only the option parser dest
        #     entries, rather than the command line options.
        #
        import re
        for opt in parser.option_list:
                if opt.help is SUPPRESS_HELP:
                        continue

                #
                # Don't display anything we shouldn't be displaying
                #
                option_name= re.sub( r'.*/--', '', "%s" % opt )
                option_name= re.sub( r'^--', '', "%s" % option_name )
                if option_name in options_to_ignore:
                        continue

                default_value= parser.defaults.get( opt.dest )
                if default_value is NO_DEFAULT or default_value is None:
                        default_string= ""
                else:
                        default_string= str( default_value )

#
# TODO: Determine the variable name used and display the --option_name=variable_name
#
                if opt.action in [ 'store_true', 'store_false' ]:
                   print """    <option id="%s" type="%s" default="%s" help="%s" />
""" % ( option_name, "boolean", default_string, quote(opt.help),  )

                else:
                   target= opt.dest.lower()
                   print """    <option id="%s" type="%s" default="%s" target="%s" help="%s" />
""" % ( option_name, opt.type, quote(default_string), target, quote(opt.help), )


        #
        # Close the table elements
        #
        print """
</configuration>
"""
        sys.exit( 0 )



    def parseOptions(self):
        """
        Uses the optparse parse previously populated and performs common options.
        """

        if self.noopts:
            args = []
        else:
            import sys
            args = sys.argv[1:]
        (self.options, self.args) = self.parser.parse_args(args=args)

        if self.options.genconf:
            self.generate_configs( self.parser, self.options )

        if self.options.genxmltable:
            self.generate_xml_table( self.parser, self.options )

        if self.options.genxmlconfigs:
            self.generate_xml_configs( self.parser, self.options )
