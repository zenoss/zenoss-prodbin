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
    import rlcompleter
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
import transaction
from Products.CMFCore.utils import getToolByName
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager
from Products.ZenUtils.Utils import zenPath

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
    from transaction import commit, abort
    from pprint import pprint

    # Connect to the database, set everything up
    app = Zope2.app()

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

    def login(username='admin'):
        utool = getToolByName(app, 'acl_users')
        user = utool.getUserById(username)
        user = user.__of__(utool)
        newSecurityManager(None, user)

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


class HistoryConsole(code.InteractiveConsole):
    """
    Subclass the default InteractiveConsole to get readline history
    """
    def __init__(self, locals=None, filename="<console>",
                 histfile=zenPath('.pyhistory')):
        code.InteractiveConsole.__init__(self, locals, filename)
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

    _banner=("Welcome to the Zenoss dmd command shell!\n"
             "'dmd' is bound to the DataRoot. 'zhelp()' to get a list of"
             "commands.")

    # Start up the console
    myconsole = HistoryConsole(locals=_customStuff())
    myconsole.interact(_banner)

