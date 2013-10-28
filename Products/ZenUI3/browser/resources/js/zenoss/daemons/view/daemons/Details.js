/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){

    Ext.define('Daemons.view.daemons.Details' ,{
        extend: 'Ext.Panel',
        alias: 'widget.daemonsdetails',
        title: _t('Details'),
        initComponent: function() {
            this.html = 'details section';
            this.callParent(arguments);
        }
    });
})();