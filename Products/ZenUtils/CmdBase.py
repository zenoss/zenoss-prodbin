##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__="""CmdBase

Provide utility functions for logging and config file parsing
to command-line programs
"""

import os
import os.path
import sys
import datetime
import logging
import re
from copy import copy
import zope.component
from zope.traversing.adapters import DefaultTraversable
from Products.Five import zcml

from optparse import (
        OptionParser, OptionGroup, Option,
        SUPPRESS_HELP, NO_DEFAULT, OptionValueError, BadOptionError,
    )
from urllib import quote

# There is a nasty incompatibility between pkg_resources and twisted.
# This pkg_resources import works around the problem.
# See http://dev.zenoss.org/trac/ticket/3146 for details
from Products.ZenUtils.PkgResources import pkg_resources

from Products.ZenUtils.Utils import unused, load_config_override, zenPath, getAllParserOptionsGen
from Products.ZenUtils.GlobalConfig import _convertConfigLinesToArguments, applyGlobalConfToParser
unused(pkg_resources)

class DMDError: pass


def checkLogLevel(option, opt, value):
    if re.match(r'^\d+$', value):
        value = int(value)
    else:
        intval = getattr(logging, value.upper(), None)
        if intval:
            value = intval
        else:
            raise OptionValueError('"%s" is not a valid log level.' % value)

    return value

def remove_args(argv, remove_args_novals, remove_args_vals):
    """
    Removes arguments from the argument list. Arguments in
    remove_args_novals have no arguments. Arguments in
    remove_args_vals have arguments, either in the format
    --arg=<val> or --arg <val>.
    """
    new_args = []
    it = iter(argv)
    for arg in it:
        if arg in remove_args_novals:
            continue
        add_arg = True
        for remove_arg in remove_args_vals:
            if remove_arg == arg:
                add_arg = False
                it.next() # Skip the argument value
                break
            elif arg.startswith(remove_arg + '='):
                add_arg = False
                break
        if add_arg:
            new_args.append(arg)
    return new_args

class LogSeverityOption(Option):
    TYPES = Option.TYPES + ("loglevel",)
    TYPE_CHECKER = copy(Option.TYPE_CHECKER)
    TYPE_CHECKER["loglevel"] = checkLogLevel


class CmdBase(object):
    """
    Class used for all Zenoss commands
    """

    doesLogging = True

    def __init__(self, noopts=0, args=None):
        zope.component.provideAdapter(DefaultTraversable, (None,))
        # This explicitly loads all of the products - must happen first!
        from OFS.Application import import_products
        import_products()
        #make sure we aren't in debug mode
        import Globals
        Globals.DevelopmentMode = False
        # We must import ZenossStartup at this point so that all Zenoss daemons
        # and tools will have any ZenPack monkey-patched methods available.
        import Products.ZenossStartup
        unused(Products.ZenossStartup)
        zcml.load_site()
        import Products.ZenWidgets
        load_config_override('scriptmessaging.zcml', Products.ZenWidgets)

        self.usage = "%prog [options]"
        self.noopts = noopts
        self.inputArgs = args

        # inputArgs was created to allow unit tests to pass in command line
        # arguments and get around whatever Zope was doing to sys.argv.
        if self.inputArgs is None:
            self.inputArgs = sys.argv[1:]

        self.parser = None
        self.args = []

        self.buildParser()
        self.buildOptions()

        # Get defaults from global.conf. They will be overridden by
        # daemon-specific config file or command line arguments.
        applyGlobalConfToParser(self.parser)
        self.parseOptions()
        if self.options.configfile:
            self.parser.defaults = self.getConfigFileDefaults(self.options.configfile)
            # We've updated the parser with defaults from configs, now we need
            # to reparse our command-line to get the correct overrides from
            # the command-line
            self.parseOptions()

        if self.doesLogging:
            self.setupLogging()


    def buildParser(self):
        """
        Create the options parser
        """
        if not self.parser:
            from Products.ZenModel.ZenossInfo import ZenossInfo
            try:
                zinfo= ZenossInfo('')
                version= str(zinfo.getZenossVersion())
            except Exception:
                from Products.ZenModel.ZVersion import VERSION
                version= VERSION
            self.parser = OptionParser(usage=self.usage,
                                       version="%prog " + version,
                                       option_class=LogSeverityOption)


    def buildOptions(self):
        """
        Basic options setup. Other classes should call this before adding
        more options
        """
        self.buildParser()
        if self.doesLogging:
            group = OptionGroup(self.parser, "Logging Options")
            group.add_option(
                '-v', '--logseverity',
                dest='logseverity', default='INFO', type='loglevel',
                help='Logging severity threshold',
            )
            group.add_option(
                '--logpath', dest='logpath', default=zenPath('log'), type='str',
                help='Override the default logging path; default $ZENHOME/log'
            )
            group.add_option(
                '--maxlogsize',
                dest='maxLogKiloBytes', default=10240, type='int',
                help='Max size of log file in KB; default 10240',
            )
            group.add_option(
                '--maxbackuplogs',
                dest='maxBackupLogs', default=3, type='int',
                help='Max number of back up log files; default 3',
            )
            self.parser.add_option_group(group)

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


    def parseOptions(self):
        """
        Uses the optparse parse previously populated and performs common options.
        """

        if self.noopts:
            args = []
        else:
            args = self.inputArgs

        (self.options, self.args) = self.parser.parse_args(args=args)

        if self.options.genconf:
            self.generate_configs( self.parser, self.options )

        if self.options.genxmltable:
            self.generate_xml_table( self.parser, self.options )

        if self.options.genxmlconfigs:
            self.generate_xml_configs( self.parser, self.options )


    def getConfigFileDefaults(self, filename, correctErrors=True):
        # TODO: This should be refactored - duplicated code with CmdBase.
        """
        Parse a config file which has key-value pairs delimited by white space,
        and update the parser's option defaults with these values.

        @parameter filename: name of configuration file
        @type filename: string
        """

        options = self.parser.get_default_values()
        lines = self.loadConfigFile(filename)
        if lines:
            lines, errors = self.validateConfigFile(filename, lines,
                                                    correctErrors=correctErrors)

            args = self.getParamatersFromConfig(lines)
            try:
                self.parser._process_args([], args, options)
            except (BadOptionError, OptionValueError) as err:
                print >>sys.stderr, 'WARN: %s in config file %s' % (err, filename)

        return options.__dict__


    def getGlobalConfigFileDefaults(self):
        # Deprecated: This method is going away - it is duplicated in GlobalConfig.py
        """
        Parse a config file which has key-value pairs delimited by white space,
        and update the parser's option defaults with these values.
        """

        filename = zenPath('etc', 'global.conf')
        options = self.parser.get_default_values()
        lines = self.loadConfigFile(filename)
        if lines:
            args = self.getParamatersFromConfig(lines)

            try:
                self.parser._process_args([], args, options)
            except (BadOptionError, OptionValueError):
                # Ignore it, we only care about our own options as defined in the parser
                pass

        return options.__dict__


    def loadConfigFile(self, filename):
        # TODO: This should be refactored - duplicated code with CmdBase.
        """
        Parse a config file which has key-value pairs delimited by white space.

        @parameter filename: path to the configuration file
        @type filename: string
        """
        lines = []
        if not os.path.exists(filename):
            return lines
        try:
            with open(filename) as file:
                for line in file:
                    if line.lstrip().startswith('#') or line.strip() == '':
                        lines.append(dict(type='comment', line=line))
                    else:
                        try:
                            # add default blank string for keys with no default value
                            # valid delimiters are space, ':' and/or '=' (see ZenUtils/config.py)
                            key, value = (re.split(r'[\s:=]+', line.strip(), 1) + ['',])[:2]
                        except ValueError:
                            lines.append(dict(type='option', line=line, key=line.strip(), value=None, option=None))
                        else:
                            option = self.parser.get_option('--%s' % key)
                            lines.append(dict(type='option', line=line, key=key, value=value, option=option))
        except IOError as e:
            errorMessage = ('WARN: unable to read config file {filename} '
                '-- skipping. ({exceptionName}: {exception})').format(
                filename=filename,
                exceptionName=e.__class__.__name__,
                exception=e
            )
            print >>sys.stderr, errorMessage
            return []

        return lines


    def validateConfigFile(self, filename, lines, correctErrors=True, warnErrors=True):
        """
        Validate config file lines which has key-value pairs delimited by white space,
        and validate that the keys exist for this command's option parser. If
        the option does not exist or has an empty value it will comment it out
        in the config file.

        @parameter filename: path to the configuration file
        @type filename: string
        @parameter lines: lines from config parser
        @type lines: list
        @parameter correctErrors: Whether or not invalid conf values should be
            commented out.
        @type correctErrors: boolean
        """

        output = []
        errors = []
        validLines = []
        date = datetime.datetime.now().isoformat()
        errorTemplate = '## Commenting out by config parser (%s) on %s: %%s\n' % (
                sys.argv[0], date)

        for lineno, line in enumerate(lines):
            if line['type'] == 'comment':
                output.append(line['line'])
            elif line['type'] == 'option':
                if line['value'] is None:
                    errors.append((lineno + 1, 'missing value for "%s"' % line['key']))
                    output.append(errorTemplate % 'missing value')
                    output.append('## %s' % line['line'])
                elif line['option'] is None:
                    errors.append((lineno + 1, 'unknown option "%s"' % line['key']))
                    output.append(errorTemplate % 'unknown option')
                    output.append('## %s' % line['line'])
                else:
                    validLines.append(line)
                    output.append(line['line'])
            else:
                errors.append((lineno + 1, 'unknown line "%s"' % line['line']))
                output.append(errorTemplate % 'unknown line')
                output.append('## %s' % line['line'])

        if errors:
            if correctErrors:
                for lineno, message in errors:
                    print >>sys.stderr, 'INFO: Commenting out %s on line %d in %s' % (message, lineno, filename)

                with open(filename, 'w') as file:
                    file.writelines(output)

            if warnErrors:
                for lineno, message in errors:
                    print >>sys.stderr, 'WARN: %s on line %d in %s' % (message, lineno, filename)

        return validLines, errors


    def getParamatersFromConfig(self, lines):
        # Deprecated: This method is going away
        return _convertConfigLinesToArguments(self.parser, lines)


    def setupLogging(self):
        """
        Set common logging options
        """
        rlog = logging.getLogger()
        rlog.setLevel(logging.WARN)
        mname = self.__class__.__name__
        self.log = logging.getLogger("zen."+ mname)
        zlog = logging.getLogger("zen")
        try:
            loglevel = int(self.options.logseverity)
        except ValueError:
            loglevel = getattr(logging, self.options.logseverity.upper(), logging.INFO)
        zlog.setLevel(loglevel)

        logdir = self.checkLogpath()
        if logdir:
            logfile = os.path.join(logdir, mname.lower()+".log")
            maxBytes = self.options.maxLogKiloBytes * 1024
            backupCount = self.options.maxBackupLogs
            h = logging.handlers.RotatingFileHandler(logfile, maxBytes=maxBytes,
                                                     backupCount=backupCount)
            h.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s",
                "%Y-%m-%d %H:%M:%S"))
            rlog.addHandler(h)
        else:
            logging.basicConfig()


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
                except OSError:
                    raise SystemExit("logpath:%s doesn't exist and cannot be created" % logdir)
            elif not os.path.isdir(logdir):
                raise SystemExit("logpath:%s exists but is not a directory" % logdir)
            return logdir


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
        for opt in getAllParserOptionsGen(parser):
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
        for opt in getAllParserOptionsGen(parser):
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
        for opt in getAllParserOptionsGen(parser):
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
