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

import logging
log = logging.getLogger('zen.ZenRRD.CommandParser')

from pprint import pformat

class ParsedResults:

    def __init__(self):
        self.events = []                # list of event dictionaries
        self.values = []                # list of (DataPointConfig, value)
        
    def __repr__(self):
        args = (pformat(self.events), pformat(self.values))
        return "ParsedResults\n  events: %s\n  values: %s}" % args

class CommandParser:

    def dataForParser(self, context, datapoint):
        return {}
    
    def processResults(self, cmd, results):
        """
        Process the results of a running a command.
        
        @type cmd: Products.ZenRRD.zencommand.Cmd
        
        @param cmd: the results of running a command, with the
        configuration from ZenHub
        @param results: the values and events from the command output
        @return: None.
        """
        raise NotImplementedError


ParserCache = {}

def _getParser(name):
    """
    Import and create the parser for this command
    """
    try:
        return ParserCache[name]
    except KeyError:
        from Products.ZenUtils.Utils import importClass
        klass = importClass('Products.ZenRRD.parsers.' + name)
        instance = klass()
        ParserCache[name] = instance
        return instance

def _getPackParser(name):
    """
    Import and create the parser for this command
    """
    try:
        return ParserCache[name]
    except KeyError:
        from Products.ZenUtils.Utils import importClass
        klass = importClass(name)
        instance = klass()
        ParserCache[name] = instance
        return instance

def getParser(name):
    """
    Import and create the parser for this command
    """
    err = ImportError("%s not found" % name)
    try:
        return _getParser(name)
    except ImportError, err:
        msg = "%s is not a core parser. Attempting to import it from " \
              "installed zenpacks."
        log.debug(msg, name)
        return _getPackParser(name)
            

def getParserNames(dmd):
    "Get the list of all parsers"

    def looksLikeAPlugin(f):
        if not f.startswith('_') and f.endswith('.py'):
            return f[:-3]
    
    import os
    from Products.ZenUtils.Utils import zenPath
    result = []
    for d, ds, fs in os.walk(zenPath('Products','ZenRRD', 'parsers')):
        for f in fs:
            plugin = looksLikeAPlugin(f)
            if plugin:
                plugin = os.path.join(d, plugin)
                plugin = plugin.split(os.path.sep)
                plugin = plugin[plugin.index('parsers') + 1:]
                plugin = '.'.join(plugin)
                result.append(plugin)

    for pack in dmd.ZenPackManager.packs():
        root = pack.path('parsers')
        for d, ds, fs in os.walk(root):
            for f in fs:
                plugin = looksLikeAPlugin(f)
                if plugin:
                    plugin = os.path.join(d, plugin)
                    plugin = plugin.split(os.path.sep)
                    plugin = plugin[plugin.index('ZenPacks'):]
                    plugin = '.'.join(plugin)
                    result.append(plugin)
    return sorted(result)
    
