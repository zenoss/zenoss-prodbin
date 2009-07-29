#!/usr/bin/env python2.4
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

import os
import code
import atexit
from optparse import OptionParser
try:
    import readline
    from rlcompleter import Completer
except ImportError:
    readline = rlcompleter = None

# Parse the command line for host and port; have to do it before Zope
# configuration, because it hijacks option parsing.
parser = OptionParser()
parser.add_option('--host',
            dest="host",default=None,
            help="hostname of zeo server")
parser.add_option('--port',
            dest="port",type="int", default=None,
            help="port of zeo server")
opts, args = parser.parse_args()

# Zope magic ensues!
import Zope2
CONF_FILE = os.path.join(os.environ['ZENHOME'], 'etc', 'zope.conf')
Zope2.configure(CONF_FILE)

# Now we have the right paths, so we can do the rest of the imports
from Products.CMFCore.utils import getToolByName
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager
from Products.ZenUtils.Utils import zenPath, set_context

_CUSTOMSTUFF = []


def set_db_config(host=None, port=None):
    # Modify the database configuration manually
    from App.config import getConfiguration
    serverconfig = getConfiguration().databases[1].config.storage.config
    xhost, xport = serverconfig.server[0].address
    if host: xhost = host
    if port: xport = port
    serverconfig.server[0].address = (xhost, xport)


def _customStuff():
    """
    Everything available in the console is defined here.
    """

    import socket
    from transaction import commit
    from pprint import pprint

    # Connect to the database, set everything up
    app = Zope2.app()
    app = set_context(app)

    def login(username='admin'):
        utool = getToolByName(app, 'acl_users')
        user = utool.getUserById(username)
        if user is None:
            user = app.zport.acl_users.getUserById(username)
        user = user.__of__(utool)
        newSecurityManager(None, user)

    login('admin')

    # Useful references
    zport = app.zport
    dmd   = zport.dmd
    sync  = zport._p_jar.sync
    find  = dmd.Devices.findDevice
    devices = dmd.Devices
    me = find(socket.getfqdn())

    def reindex():
        sync()
        dmd.Devices.reIndex()
        dmd.Events.reIndex()
        dmd.Manufacturers.reIndex()
        dmd.Networks.reIndex()
        commit()

    def logout():
        noSecurityManager()

    def zhelp():
        cmds = filter(lambda x: not x.startswith("_"), _CUSTOMSTUFF)
        cmds.sort()
        for cmd in cmds: print cmd

    def grepdir(obj, regex=""):
        if regex:
            import re
            pattern = re.compile(regex)
            for key in dir(obj):
                if pattern.search(key):
                    print key

    def cleandir(obj):
        portaldir = set(dir(dmd))
        objdir = set(dir(obj))
        appdir = set(dir(app))
        result = list(objdir - portaldir - appdir)
        result.sort()
        pprint(result)


    _CUSTOMSTUFF = locals()
    return _CUSTOMSTUFF

class ZenCompleter(Completer):
    """
    Provides the abiility to specify *just* the zendmd-specific 
    stuff when you first enter and hit tab-tab, and also the 
    ability to remove junk that we don't need to see.
    """
    ignored_names = [
        "COPY", "DELETE", "HEAD", "HistoricalRevisions",
        "LOCK", "MKCOL", "MOVE", "OPTIONS",
        "Open", "PROPFIND", "PROPPATCH",
        "PUT", "REQUEST", "SQLConnectionIDs",
        "SiteRootAdd", "TRACE", "UNLOCK",
        "ac_inherited_permissions",
        "access_debug_info",
        "bobobase_modification_time",
        "manage_historyCompare",
        "manage_historyCopy",
        "manage_addDTMLDocument",
        "manage_addDTMLMethod",
        "manage_clone",   
        "manage_copyObjects",
        "manage_copyright",
        "manage_cutObjects",
        "manage_historicalComparison",
        "validClipData",
        "manage_CopyContainerAllItems",
        "manage_CopyContainerFirstItem",
        "manage_DAVget",
        "manage_FTPlist",
        "manage_UndoForm",
        "manage_access",   
    ]
    ignored_prefixes = [
       '_', 'wl_', 'cb_', 'acl', 'http__', 'dav_',
       'manage_before', 'manage_after',
       'manage_acquired',
    ]

    def global_matches(self, text):
        """
        Compute matches when text is a simple name.
        """
        matches = []
        for name in self.namespace:
            if name.startswith(text):
                matches.append(name)

        return matches

    def attr_matches(self, text):
        """
        Compute matches when text contains a dot.
        """
        matches = []
        for name in Completer.attr_matches(self, text):
            if name.endswith("__roles__"):
                continue
            component = name.split('.')[-1]
            if component in self.ignored_names:
                continue
            ignore = False
            for prefix in self.ignored_prefixes:
                if component.startswith(prefix):
                    ignore = True
                    break

            if not ignore:
                matches.append(name)

        return matches
        #return filter(lambda x: not x.endswith("__roles__"),
                      #Completer.attr_matches(self, text))



class HistoryConsole(code.InteractiveConsole):
    """
    Subclass the default InteractiveConsole to get readline history
    """
    def __init__(self, locals=None, filename="<console>",
                 histfile=zenPath('.pyhistory')):
        code.InteractiveConsole.__init__(self, locals, filename)
        if readline is not None:
            completer = ZenCompleter(locals)
            readline.set_completer(completer.complete)
            readline.parse_and_bind("tab: complete")
        self.init_history(histfile)


    def init_history(self, histfile):
        if hasattr(readline, "read_history_file"):
            try:
                readline.read_history_file(histfile)
            except IOError:
                pass
            atexit.register(self.save_history, histfile)

    def save_history(self, histfile):
        readline.write_history_file(histfile)


if __name__=="__main__":
    # Do we want to connect to a database other than the one specified in
    # zope.conf?
    if opts.host or opts.port:
        set_db_config(opts.host, opts.port)

    _banner = ["Welcome to the Zenoss dmd command shell!\n"
             "'dmd' is bound to the DataRoot. 'zhelp()' to get a list of "
             "commands." ] 
    if readline is not None:
        _banner = '\n'.join( [ _banner[0],
                       "Use TAB-TAB to see a list of zendmd related commands.",
                       "Tab completion also works for objects -- hit tab after"
                       " an object name and '.'", " (eg dmd. + tab-key)."])

    # Start up the console
    myconsole = HistoryConsole(locals=_customStuff())
    myconsole.interact(_banner)

