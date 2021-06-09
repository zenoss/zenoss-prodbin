##############################################################################
#
# Copyright (C) Zenoss, Inc. 2021, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

# TEMPORARY
# The wrapt utility wraps functions, intercepting calls, allowing for modification.
# This is used to correct behavior as needed in ZenPacks when running via ZPA.
# These definitions should be kept separate and isolated.
#
# This file is loaded by Products.ZenUtils (__init__.py)
import wrapt
import logging
LOG = logging.getLogger("zen.wrapt")

from db import get_db
_DB = None
def obj_db():
    global _DB
    if _DB == None:
        _DB = get_db()
        _DB.load()
    return _DB

def wrapper_getParserLoader(_getParserLoader, instance, args, kwargs):
    try:
        _dmd = args[0]
        _modPath = args[1]
        parser = _getParserLoader(*args, **kwargs)
        # --> return MonitoringManager.getInstance().getPluginLoader(dmd.ZenPackManager.packs(), modPath)
        # dmd.ZenPackManager does not exist in ZPA
    except Exception as ex:
        try:
            from Products.DataCollector.Plugins import MonitoringManager
            parser = MonitoringManager.getInstance().getPluginLoader([], _modPath)
        except Exception as exc:
            parser = None
            LOG.error("Wrapt caught exception in Products.DataCollector.Plugins.getParserLoader; %s", exc)
    return parser
import Products.DataCollector.Plugins as Plugins
wrapt.wrap_function_wrapper(Plugins, 'getParserLoader', wrapper_getParserLoader)


def wrapped_params(_params, instance, args, kwargs):
    rrrdDS = args[0]
    winDev = args[1]
    try:
        if hasattr(winDev, 'getDmd') and not hasattr(winDev, 'dmd'):
            dmd = winDev.getDmd()
            setattr(winDev, 'dmd', dmd)
            LOG.info("Wrapt updated Windows Device's dmd reference")
        return _params(*args, **kwargs)
    except Exception as ex:
        LOG.error("Wrapt caught exception in setting params for ShellDataSourcePlugin: %s", ex)
from ZenPacks.zenoss.Microsoft.Windows.datasources.ShellDataSource import ShellDataSourcePlugin as WinDSPlugin
wrapt.wrap_function_wrapper(WinDSPlugin, 'params', wrapped_params)


def wrapped_txwinrm_createConnectionInfo(_createConnectionInfo, instance, args, kwargs):
    mod = "txwinrm.createConnectionInfo"
    device_proxy = args[0]
    devId = device_proxy.device if hasattr(device_proxy, 'device') else getattr(device_proxy, 'id', None)
    zobjDev = obj_db().devices.get(devId)

    def set_prop(zprop, alt_name):
        if not getattr(device_proxy, zprop, None):
            value = getattr(device_proxy, alt_name, None)
            if not value and zobjDev:
                value = zobjDev.zProperties.get(alt_name, None)
            if value:
                setattr(device_proxy, zprop, value)

    try:
        set_prop('windows_servername', 'zWinRMServerName')
        set_prop('windows_password', 'zWinRMPassword')
        set_prop('windows_user', 'zWinRMUser')
        if not getattr(device_proxy, 'windows_user', None):
            set_prop('windows_user', 'zWinUser')
        result = _createConnectionInfo(*args, **kwargs)
    except Exception as exConn:
        LOG.error("Error creating connection: %s  \n%s", exConn, traceback.format_exc())
        result = None
    return result
import ZenPacks.zenoss.Microsoft.Windows.txwinrm_utils as WinMod
wrapt.wrap_function_wrapper(WinMod, 'createConnectionInfo', wrapped_txwinrm_createConnectionInfo)


def wrapped_shellDSCollect(_collect, instance, args, kwargs):
    config = args[0]
    dsconf0 = config.datasources[0]
    zobjDev = obj_db().devices.get(dsconf0.device)
    def set_prop(name):
        if not hasattr(dsconf0, name) and zobjDev:
            value = zobjDev.zProperties.get(name, None)
            if value:
                setattr(dsconf0, name, value)
    try:
        set_prop('zWinRMServerName')
        set_prop('zWinRMUser')
        set_prop('zWinRMPassword')
    except Exception as exConn:
        LOG.error("Error updating dsconf[0]: %s  \n%s", exConn, traceback.format_exc())
        result = None
    _collect(*args, **kwargs)

from ZenPacks.zenoss.Microsoft.Windows.datasources.ShellDataSource import ShellDataSourcePlugin as ShellDS
wrapt.wrap_function_wrapper(ShellDS, 'collect', wrapped_shellDSCollect)
