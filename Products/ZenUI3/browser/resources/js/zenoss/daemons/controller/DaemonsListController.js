/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){

    /**
     * @class Daemons.controller.DaemonsListController
     * This is the controller for the list of control plane services and collector deamons.
     * @extends Ext.app.Controller
     */
    Ext.define('Daemons.controller.DaemonsListController', {
        models: ["Daemon"],
        views: [
            "daemons.List"
        ],
        extend: 'Ext.app.Controller'
        //the rest of the Controller here
    });
})();
