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

__doc__='''ZenModel.migrate.__init__.py

Use __init__.py to get all the upgrade modules imported.

$Id$
'''

__version__ = "$Revision$"[11:-2]

# by virtue of being a migration script, we often import deprecated modules
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

import eventdbname
import evtprops
import kill_cricket
import reindex_history
import hoist_perf_data
import interfacename_convert
import processes
import mibs
import clearid
import mwrelations
import rrdmin
import winminseverity
import nocountprocs
import command
import perfxmlrpc
import import_export_filesystem
import datapoints
import about_zenoss
import ar_schedule
import advanced_query
import wmiignore
import pas_conversion
import indexhtml
import zcollectordecoding
import standarderrormessage
import innodb
import loadaveragereport
import casesensitive_catalogs
import zlinks
import smtpsnpp
import monitors
import usercommands
import rrdcpu
import changeeventclasses
import reportserver
import devicepriority
import rrdmin2
#import changeeventaction
import event_commands
import statusconnecttimeout
import procparams
import keypath
import maxoids
import betterstandarderrormessage
import event_newclasses
import defaultcommandtimeout
import eventclassmapping
import zenuilayer
#import packs
import menus
import deviceTemplatesProperty
import zlocal
import evenbetterstandarderrormessage
import zCollectorPlugins
import zenpackdatasources
import zpropscleanup
import processsequence
import zWmiMonitorProperty
import device_indexes
import addWinService
import convertOSSSoftwareClass
import zCollectorLogChanges
import twopointohobjects
import addexpectregex
