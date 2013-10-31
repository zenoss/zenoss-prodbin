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

        /**
         * This is a list of daemons that are currently restarting.
         * when it is not empty we will periodically check the server to get the
         * status and when it is not restarting anymore we update the icon.
         **/
        restartingDaemons: {},

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
                },
                // Column Actions
                // restart
                'daemonslist actioncolumn[ref="restartcolumn"]': {
                    click: Ext.bind(function(grid, cell, colIdx, rowIdx, event, record) {
                        this.updateRefreshIcon([record]);
                        this.updateSelectedDeamons([record], 'restart', 'state', Daemons.states.UP);
                    }, this)
                },
                // start/stop
                'daemonslist actioncolumn[ref="statuscolumn"]': {
                    click: Ext.bind(function(grid, cell, colIdx, rowIdx, event, record) {
                        // find out if we need to stop or start the record
                        if (record.get('state')) {
                            this.updateSelectedDeamons([record], 'stop', 'state', Daemons.states.DOWN);
                        } else {
                            this.updateSelectedDeamons([record], 'start', 'state', Daemons.states.UP);
                        }
                    }, this)
                },
                // enable/disable
                'daemonslist actioncolumn[ref="autostart"]': {
                    click: Ext.bind(function(grid, cell, colIdx, rowIdx, event, record) {
                        this.setAutoStartDaemons([record], !record.get('autostart'));
                    }, this)
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
                                       'start', 'state', Daemons.states.UP);
        },
        /**
         * Stops every daemon that is selected
         **/
        stopSelectedDeamons: function() {
            this.updateSelectedDeamons(this.getTreegrid().getSelectionModel().getSelection(),
                                       'stop', 'state', Daemons.states.DOWN);
        },
        /**
         * restarts every daemon that is selected
         **/
        restartSelectedDeamons: function() {
            var selected = this.getTreegrid().getSelectionModel().getSelection();
            this.updateRefreshIcon(selected);
            this.updateSelectedDeamons(selected, 'restart', 'state', Daemons.states.UP);
        },

        /**
         * Let the user know that the deamon is restarting.
         **/
        updateRefreshIcon: function(selectedRows) {
            var store = this.getTreegrid().getStore(),
                view = this.getTreegrid().getView(),
                i, index, el,
                images = this.getTreegrid().getView().getEl().query('.restarticon');
            for (i=0;i<selectedRows.length;i++) {
                el = view.getNode(selectedRows[i]).getElementsByClassName('restarticon')[0];
                el.src = '/++resource++zenui/img/ext4/icon/circle_arrows_ani.gif';
                this.restartingDaemons[selectedRows[i].get('id')] = {
                    row: selectedRows[i],
                    el: el
                };
            }
            this.pollForChanges();
        },

        /**
         * This periodically checks the current restarting daemons to see if they have finished
         * restarting.
         **/
        pollForChanges: function() {
            if (Ext.Object.getKeys(this.restartingDaemons).length == 0) {
                return;
            }
            if (!this.restartingTask) {
                this.restartingTask = new Ext.util.DelayedTask(this.doCheckForRestarting, this);
            }
            this.restartingTask.delay(1000);
        },
        doCheckForRestarting: function() {
            for (var daemon in this.restartingDaemons ) {
                function callback(response) {
                    var id = response.data.id;
                    if (!response.data.isRestarting) {
                        var record = this.restartingDaemons[id];
                        record.el.src = '/++resource++zenui/img/ext4/icon/circle_arrows_still.png';
                        delete this.restartingDaemons[id];
                    }
                }
                // check the server to see if we are still restarting
                router.getInfo({
                    id: this.restartingDaemons[daemon].row.get('id')
                }, callback, this);
            }
            this.pollForChanges();
        },

        /**
         * Updates the enabled flag for all the rows passed in.
         **/
        setAutoStartDaemons: function(rows, enabled) {
            var uids = [], i;
            for (i=0; i<rows.length; i++) {
                uids.push(rows[i].get('uid'));
                rows[i].set("autostart", enabled);
            }
            router.setAutoStart({
                uids: uids,
                enabled: enabled
            });
        }
    });
})();
