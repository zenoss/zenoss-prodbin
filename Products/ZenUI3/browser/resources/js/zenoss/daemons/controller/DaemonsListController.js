/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){
    var router = Zenoss.remote.ApplicationRouter;

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
        refs: [{
            ref: 'treegrid',
            selector: 'daemonslist'
        }],
        extend: 'Ext.app.Controller',
        init: function() {
            // toolbar button handlers
            this.control({
                // start
                'daemonslist button[ref="start"]': {
                    click: this.startSelectedDeamons
                },
                // stop
                'daemonslist button[ref="stop"]': {
                    click: this.stopSelectedDeamons
                },
                // restart
                'daemonslist button[ref="restart"]': {
                    click: this.restartSelectedDeamons
                }
            });
        },
        /**
         * Updates the model representation of the selected rows
         * this will update the view as well.
         **/
        updateRows: function(selectedRows, field, value) {
            var i;
            for(i=0;i<selectedRows.length;i++) {
                selectedRows[i].set(field, value);
            }
        },
        /**
         * Performs the "action" on every selected daemon.
         **/
        updateSelectedDeamons: function(selectedRows, action, field, value) {
            var grid = this.getTreegrid(),
                uids = [], i=0;
            if (selectedRows.length) {
                // get a list of ids from the server
                for(i=0;i<selectedRows.length;i++) {
                    uids.push(selectedRows[i].get('uid'));
                }
                // call the server
                router[action]({
                    uids: uids
                }, function(response) {
                    if (response.success) {
                        // this will update the grid without refreshing it
                        this.updateRows(selectedRows, field, value);
                    }
                }, this);
            }
        },
        /**
         * Starts every daemon that is selected
         **/
        startSelectedDeamons: function() {
            this.updateSelectedDeamons(this.getTreegrid().getSelectionModel().getSelection(),
                                       'start', 'status', 'up');
        },
        /**
         * Stops every daemon that is selected
         **/
        stopSelectedDeamons: function() {
            this.updateSelectedDeamons(this.getTreegrid().getSelectionModel().getSelection(),
                                       'stop', 'status', 'down');
        },
        /**
         * restarts every daemon that is selected
         **/
        restartSelectedDeamons: function() {
            var selected = this.getTreegrid().getSelectionModel().getSelection();
            this.updateSelectedDeamons(selected, 'restart', 'status', 'up');
            this.updateRefreshIcon(selected);
        },

        /**
         * Let the user know that the deamon is restarting.
         **/
        updateRefreshIcon: function() {

        }
    });
})();
