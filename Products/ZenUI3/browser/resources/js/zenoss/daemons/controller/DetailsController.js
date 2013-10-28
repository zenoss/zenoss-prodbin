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
     * @class Daemons.controller.DetailsController
     * This is the controller for the details section of the page.
     * @extends Ext.app.Controller
     */
    Ext.define('Daemons.controller.DetailsController', {
        extend: 'Ext.app.Controller',
        views: [
            "daemons.Details"
        ]
        //the rest of the Controller here
    });
})();
