/*
  ###########################################################################
  #
  # This program is part of Zenoss Core, an open source monitoring platform.
  # Copyright (C) 2010, Zenoss Inc.
  #
  # This program is free software; you can redistribute it and/or modify it
  # under the terms of the GNU General Public License version 2 as published by
  # the Free Software Foundation.
  #
  # For complete information please visit: http://www.zenoss.com/oss/
  #
  ###########################################################################
*/

Ext.onReady(function(){

    Ext.ns('Zenoss.settings');
    var router = Zenoss.remote.ZepRouter;

    function buildPropertyGrid(response) {
        var propsGrid,
            data;
        data = response.data;
        propsGrid = new Zenoss.form.SettingsGrid({
            renderTo: 'propList',
            width: 500,
            saveFn: router.setConfigValues
        }, data);
    }

    function loadProperties() {
        router.getConfig({}, buildPropertyGrid);
    }

    loadProperties();

});