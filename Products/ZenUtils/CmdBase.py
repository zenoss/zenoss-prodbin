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
to command line programs


$Id: CmdBase.py,v 1.10 2004/04/04 02:22:21 edahl Exp $"""

__version__ = "$Revision: 1.10 $"[11:-2]

import os
import sys
import logging
from optparse import OptionParser, SUPPRESS_HELP, NO_DEFAULT


def parseconfig(options):
    """parse a config file which has key value pairs delimited by white space"""
    if not os.path.exists(options.configfile):
        print >>sys.stderr, "WARN: config file %s not found skipping" % (
                            options.configfile)
        return
    lines = open(options.configfile).readlines()
    for line in lines:
        if line.lstrip().startswith('#'): continue
        if line.strip() == '': continue
        key, value = line.split(None, 1)
        value = value.rstrip('\r\n')
        key = key.lower()
        defval = getattr(options, key, None)
        # hack around for #2290: ignore config file values for
        # list types when the user has provided a value
        if type(defval) == type([]) and defval: continue
        if defval: value = type(defval)(value)
        setattr(options, key, value)


class DMDError: pass

class CmdBase:
    
    doesLogging = True

    def __init__(self, noopts=0):
        self.usage = "%prog [options]"
        self.noopts = noopts
        self.args = []
        self.parser = None
        self.buildParser()
        self.buildOptions()
        self.parseOptions()
        if self.options.configfile:
            parseconfig(self.options)
        if self.doesLogging:
            self.setupLogging()


    def setupLogging(self):
        rlog = logging.getLogger()
        rlog.setLevel(logging.WARN)
        mname = self.__class__.__name__
        self.log = logging.getLogger("zen."+ mname)
        zlog = logging.getLogger("zen")
        zlog.setLevel(self.options.logseverity)
        if self.options.logpath:
            logdir = self.options.logpath
            if not os.path.isdir(os.path.dirname(logdir)):
                raise SystemExit("logpath:%s doesn't exist" % logdir)
            logfile = os.path.join(logdir, mname.lower()+".log")
            h = logging.FileHandler(logfile)
            h.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s",
                "%Y-%m-%d %H:%M:%S"))
            rlog.addHandler(h)
        else:
            logging.basicConfig()


    def buildParser(self):
        if not self.parser:
            self.parser = OptionParser(usage=self.usage, 
                                       version="%prog " + __version__)

    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        self.buildParser()
        if self.doesLogging:
            self.parser.add_option('-v', '--logseverity',
                        dest='logseverity',
                        default=20,
                        type='int',
                        help='Logging severity threshold')
            self.parser.add_option('--logpath',dest='logpath',
                        help='override default logging path')
        self.parser.add_option("-C", "--configfile", 
                    dest="configfile",
                    help="config file must define all params (see man)")



    def pretty_print_config_comment( self, comment ):
        """Quick and dirty pretty printer for comments that happen to be longer than can comfortably
be seen on the display."""

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
                if index != -1:
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
        """Create a configuration file based on the long-form of the option names"""

	#
	# Header for the configuration file
	#
	daemon_name= os.path.basename( sys.argv[0] )
	daemon_name= daemon_name.replace( '.py', '' )

	print """#
# Configuration file for %s
#
#  To enable a particular option, uncomment the desired entry.
#
# Parameter	Setting
# ---------	-------""" % ( daemon_name )


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
        """Create a Docbook table based on the long-form of the option names"""

	#
	# Header for the configuration file
	#
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



    def parseOptions(self):

        self.parser.add_option("--genconf",
                               action="store_true",
                               default=False,
                               help="Generate a template configuration file" )

        self.parser.add_option("--genxmltable",
                               action="store_true",
                               default=False,
                               help="Generate a Docbook table showing command-line switches." )

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
