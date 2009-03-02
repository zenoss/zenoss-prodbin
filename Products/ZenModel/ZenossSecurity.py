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

# Any updates to permissions in this file must be reflected in
# ZenModel/permissions.zcml.

# Zenoss Roles
ZEN_USER_ROLE = 'ZenUser'
ZEN_MANAGER_ROLE = 'ZenManager'
OWNER_ROLE = 'Owner'
MANAGER_ROLE = 'Manager'


# Zenoss Permissions
ZEN_COMMON = 'ZenCommon'
ZEN_MANAGE_DMD = 'Manage DMD'
ZEN_UPDATE = "ZenUpdate"
ZEN_DELETE = "Delete objects"
ZEN_ADD = 'Add DMD Objects'

ZEN_VIEW = 'View'
ZEN_VIEW_HISTORY = 'View History'
ZEN_VIEW_MODIFICATIONS='View Modifications'

# Events
ZEN_MANAGE_EVENTMANAGER = 'Manage EventManager'
ZEN_MANAGE_EVENTS = 'Manage Events'
ZEN_SEND_EVENTS = 'Send Events'

# User Settings
ZEN_CHANGE_SETTINGS = 'Change Settings'
ZEN_CHANGE_ALERTING_RULES = 'Change Alerting Rules'
ZEN_CHANGE_EVENT_VIEWS = 'Change Event Views'
ZEN_CHANGE_ADMIN_OBJECTS = 'Change Admin Objects'

ZEN_EDIT_USER = 'Edit Users'
ZEN_EDIT_USERGROUP = 'Edit User Groups'

# Device
ZEN_CHANGE_DEVICE = 'Change Device'
# Change Class, Rename, Delete Device, Reset IP
ZEN_ADMIN_DEVICE='Admin Device'
# Model, Lock, Reset Community, Push Changes, Clear Heartbeats
ZEN_MANAGE_DEVICE='Manage Device'
# Existing permission for setLastPollSnmpUpTime, getLastPollSnmpUpTime
ZEN_MANAGE_DEVICE_STATUS='Manage Device Status'

# Run Commands
#ZEN_COLLECTOR_PLUGINS_EDIT='Collector Plugins Edit'
#ZEN_COLLECTOR_PLUGINS_VIEW='Collector Plugins View'
ZEN_ZPROPERTIES_EDIT='zProperties Edit'
ZEN_ZPROPERTIES_VIEW='zProperties View'
ZEN_EDIT_LOCAL_TEMPLATES='Edit Local Templates'

ZEN_RUN_COMMANDS = 'Run Commands'

# Administrate
ZEN_DEFINE_COMMANDS_EDIT='Define Commands Edit'
ZEN_DEFINE_COMMANDS_VIEW='Define Commands View'
ZEN_MAINTENANCE_WINDOW_EDIT='Maintenance Windows Edit'
ZEN_MAINTENANCE_WINDOW_VIEW='Maintenance Windows View'
ZEN_ADMINISTRATORS_EDIT='Administrators Edit'
ZEN_ADMINISTRATORS_VIEW='Administrators View' 


