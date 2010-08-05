#!/bin/bash
#############################################################################
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#############################################################################
#
# This script modifies ZenPacks that will prevent v3.0 from starting up and
# completing an upgrade process. These ZenPacks will then be upgraded
# following the upgrade of core and will be functional again.
#
PATCHCMD="patch -s -N" 
find_zenpack()
{
    local zenpack_name="$1"
    unset zenpack_dir

    for zenpack in ${ZENHOME}/ZenPacks/ZenPacks*
    do
        if [[ "$zenpack" =~ "${zenpack_name}" ]]; then
            if [ -f "$zenpack" ]; then
                zenpack_dir=`head -n1 "$zenpack"`
            elif [ -d "$zenpack" ]; then
                zenpack_dir="$zenpack"
            fi
        fi 
    done
}

if [ -z "$ZENHOME" ] ; then
    echo ERROR: '$ZENHOME' is not set.
    echo This is usually caused by executing this command as root rather than \
as the zenoss user.  Either define '$ZENHOME' or run this command as a \
different user.
else
    # Setup zenoss-friendly executable search path...especially for stacks.
    . $ZENHOME/bin/zenfunctions

    #
    # Patch the Diagram ZenPack to disable loading any registered components
    # via Zope Five as they aren't compatible with the 3.0 core code.
    #
    zenpack_name="Diagram"
    find_zenpack "${zenpack_name}"
    configure_file="${zenpack_dir}/ZenPacks/zenoss/${zenpack_name}/configure.zcml"
    if [ -f "${configure_file}" ]; then
        $PATCHCMD  "${configure_file}" > /dev/null 2>&1 <<__EOF__
--- configure.zcml  2010-05-24 13:21:48.000000000 -0500
+++ /home/zenoss/configure.zcml 2010-05-28 09:08:56.000000000 -0500
@@ -3,36 +3,4 @@
     xmlns:browser="http://namespaces.zope.org/browser"
     xmlns:five="http://namespaces.zope.org/five">
 
-<include package="Products.Five.viewlet" />
-<include package="Products.Five" file="permissions.zcml" />
-<include package="Products.ZenUI3.browser" />
-
-<browser:page
-    name="diagram"
-    for="Products.ZenModel.Location.Location"
-    class=".diagram.DiagramView"
-    permission="zenoss.View"
-    />
-
-<browser:page
-    name="diagram_rainbow"
-    for="Products.ZenModel.Location.Location"
-    template="diagram_rainbow.pt"
-    permission="zenoss.View"
-    />
-
-<browser:page
-    name="diagram_router"
-    for="Products.ZenModel.Location.Location"
-    class=".diagram.DiagramData"
-    permission="zenoss.View"
-    />
-
-<browser:viewlet
-    name="diagram_api"
-    manager="Products.ZenUI3.browser.interfaces.IExtDirectAPI"
-    class=".diagram.DiagramAPIDefinition"
-    permission="zope2.Public"
-    />
-
 </configure>
__EOF__
    fi

    #
    # Patch ZenMailTx because OpenSSL bindings for python 2.6 aren't there
    # with the python 2.4 version of the ZenPack. This patch just causes
    # the warning to disappear.
    #
    zenpack_name="ZenMailTx"
    find_zenpack "${zenpack_name}"
    mail_file="${zenpack_dir}/ZenPacks/zenoss/${zenpack_name}/Mail.py"
    if [ -f "${mail_file}" ]; then
        $PATCHCMD "${mail_file}" > /dev/null 2>&1 << __EOF__
--- Mail.py 2010-05-24 13:16:55.000000000 -0500
+++ /home/zenoss/Mail.py    2010-05-28 10:21:48.000000000 -0500
@@ -14,11 +14,6 @@
 sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
 
 ssl = None
-try:
-    from twisted.internet import ssl
-except ImportError:
-    import warnings
-    warnings.warn('OpenSSL Python bindings are missing')
 
 
 import traceback
__EOF__
    fi

    #
    # Patch EnterpriseSecurity since it has a bug in its overriden ZenPack.remove
    # method that does not allow ZenPack cleanup to occur properly when the 
    # ZenPack is being upgraded.
    #
    zenpack_name="EnterpriseSecurity"
    find_zenpack "${zenpack_name}"
    init_file="${zenpack_dir}/ZenPacks/zenoss/${zenpack_name}/__init__.py"
    if [ -f "${init_file}" ]; then
      $PATCHCMD "${init_file}"  > /dev/null 2>&1 << __EOF__
--- __init__.py 2010-05-31 20:41:44.000000000 -0500
+++ __init__.py.new 2010-05-31 20:41:41.000000000 -0500
@@ -107,4 +107,5 @@
         "remove the encryption transformer"
         if not leaveObjects and 'password' in app.dmd.propertyTransformers:
             removeCrypter(app.dmd)
-            
+        ZenPackBase.remove(self, app, leaveObjects)
+
__EOF__
    fi

    #
    # Patch ZenVMware since it uses a deprecated version of json.
    #
    zenpack_name="ZenVMware"
    find_zenpack "${zenpack_name}"
    init_file="${zenpack_dir}/ZenPacks/zenoss/${zenpack_name}/__init__.py"
    if [ -f "${init_file}" ]; then
        $PATCHCMD "${init_file}" > /dev/null 2>&1 << __EOF__
--- __init__.py 2010-06-01 13:11:05.000000000 -0500
+++ __init__.py.new 2010-06-01 13:11:19.000000000 -0500
@@ -18,7 +18,7 @@
 from Products.CMFCore.DirectoryView import registerDirectory
 from Products.ZCatalog.ZCatalog import manage_addZCatalog
 from Products.ZCatalog.Catalog import CatalogError
-from Products.ZenUtils.json import json
+from Products.ZenUtils.jsonutils import json
 from Products.ZenUtils.Utils import monkeypatch
 from Products.ZenUtils.Search import makeCaseInsensitiveKeywordIndex
 from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex
__EOF__
    fi

    file="${zenpack_dir}/ZenPacks/zenoss/${zenpack_name}/VIPerfCounterMap.py"
    if [ -f "${file}" ]; then
        $PATCHCMD "${file}"  > /dev/null 2>&1 << __EOF__
--- VIPerfCounterMap.py 2010-05-24 13:19:03.000000000 -0500
+++ VIPerfCounterMap.py.new 2010-06-01 13:21:59.000000000 -0500
@@ -12,7 +12,7 @@
 from OFS.SimpleItem import SimpleItem
 from AccessControl import ClassSecurityInfo
 
-from Products.ZenUtils.json import json
+from Products.ZenUtils.jsonutils import json
 from Products.ZenModel.ZenModelItem import ZenModelItem
__EOF__
    fi

    #
    # Patch CiscoUCS to prevent the loading of any Zope components until
    # it has been upgraded.
    #
    zenpack_name="CiscoUCS"
    find_zenpack "${zenpack_name}"
    configure_file="${zenpack_dir}/ZenPacks/zenoss/${zenpack_name}/browser/configure.zcml"
    if [ -f "${configure_file}" ]; then
        $PATCHCMD  "${configure_file}"  > /dev/null 2>&1 <<__EOF__
--- configure.zcml  2010-06-28 13:03:56.000000000 -0400
+++ configure.zcml.new  2010-06-28 13:38:42.000000000 -0400
@@ -5,97 +5,4 @@
     xmlns:browser="http://namespaces.zope.org/browser"
     i18n_domain="ZenPacks.zenoss.CiscoUCS">
 
-    <include package="Products.ZenModel" file="permissions.zcml"/>
-
-    <browser:resourceDirectory
-        name="ucsui"
-        directory="resources"
-        />
-
-    <browser:page
-        for="*"
-        name="viewAddCiscoUCS"
-        class=".views.AddCiscoUCS"
-        permission="zenoss.ManageDMD"
-        />
-
-    <browser:page
-        for="*"
-        name="addCiscoUCS"
-        class=".views.AddCiscoUCS"
-        attribute="submitForm"
-        permission="zenoss.ManageDMD"
-        />
-
-    <browser:page
-        for="ZenPacks.zenoss.CiscoUCS.Chassis.Chassis"
-        name="viewChassisDetails"
-        class=".views.ChassisView"
-        permission="zenoss.View"
-        />
-
-    <browser:page
-        for="ZenPacks.zenoss.CiscoUCS.FabricInterconnect.FabricInterconnect"
-        name="viewFabricInterconnectDetails"
-        class=".views.FabricInterconnectView"
-        permission="zenoss.View"
-        />
-
-    <browser:page
-        for="ZenPacks.zenoss.CiscoUCS.SwitchCard.SwitchCard"
-        name="viewSwitchCardDetails"
-        class=".views.SwitchCardView"
-        permission="zenoss.View"
-        />
-
-    <browser:page
-        for="ZenPacks.zenoss.CiscoUCS.EthPort.EthPort"
-        name="viewEthPortDetails"
-        class=".views.EthPortView"
-        permission="zenoss.View"
-        />
-
-    <browser:page
-        for="ZenPacks.zenoss.CiscoUCS.Server.Server"
-        name="viewServerDetails"
-        class=".views.ServerView"
-        permission="zenoss.View"
-        />
-
-    <browser:page
-        for="ZenPacks.zenoss.CiscoUCS.HostEthIf.HostEthIf"
-        name="viewHostEthIfDetails"
-        class=".views.HostEthIfView"
-        permission="zenoss.View"
-        />
-
-    <browser:page
-        for="ZenPacks.zenoss.CiscoUCS.ServiceProfile.ServiceProfile"
-        name="viewServiceProfileDetails"
-        class=".views.ServiceProfileView"
-        permission="zenoss.View"
-        />
-
-    <browser:page
-        for="ZenPacks.zenoss.CiscoUCS.Device.Device"
-        name="viewServiceProfiles"
-        class=".views.ServiceProfilesView"
-        permission="zenoss.View"
-        />
-
-    <browser:page
-        for="ZenPacks.zenoss.CiscoUCS.FanModule.FanModule"
-        name="viewFanModule"
-        class=".views.FanModuleView"
-        permission="zenoss.View"
-        />
-
-    <browser:page
-        for="*"
-        name="ucs_macros"
-        class=".views.MacrosView"
-        permission="zenoss.View"
-        />
-
-    
 </configure>
__EOF__
    fi
fi

