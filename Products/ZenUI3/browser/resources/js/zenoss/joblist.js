/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
*/

Ext.onReady(function() {

Ext.ns("Zenoss.jobs");

var REMOTE = Zenoss.remote.JobsRouter;


var dateRenderer = Ext.util.Format.dateRenderer('m/d/Y h:i:s A');

function renderDate(utcseconds) {
    if (utcseconds) {
        var adjusted = utcseconds - new Date().getTimezoneOffset()*60,
            d = new Date(0);
        d.setUTCSeconds(adjusted);
        return d.readable(1);
    }
    return "--"
}


Ext.getCmp('center_panel').add({
    layout: 'border', 
    items: [{
        id: 'jobs',
        region: 'center',
        xtype: 'basegridpanel',
        uid: '/zport/dmd/JobManager',
        stateful: true,
        stateId: 'jobs',
        store: Ext.create('Zenoss.DirectStore', {
            id: 'jobliststore',
            root: 'jobs',
            autoLoad: true,
            pageSize: 500,
            initialSortColumn: 'scheduled',
            totalProperty: 'totalCount',
            model: 'Zenoss.model.Job',
            directFn: REMOTE.getJobs,
            listeners: {
                'load': function(store) {
                    store.loaded = true;
                }
            }
        }),
        columns: [{
            id: 'status',
            dataIndex: 'status',
            header: _t('Status'),
            width: 150,
            sortable: true,
            renderer: function(value) {
                var iconCls = "";
                value = Ext.util.Format.capitalize(value.toLowerCase());
                switch (value) {
                    case "Success":
                        iconCls = "tree-severity-icon-small-clear";
                        break;
                    case "Failure":
                        iconCls = "tree-severity-icon-small-critical";
                        break;
                    case "Aborted":
                        iconCls = "tree-severity-icon-small-warning";
                    default:
                        break;
                }
                return "<span style='padding-left:18px;padding-top:2px;' class='"+iconCls+"'>"+value+"</span>";
            }
        },{
            id: 'description',
            dataIndex: 'description',
            header: _t('Description'),
            flex: 3,
            sortable: false
        },{
            id: 'scheduled',
            dataIndex: 'scheduled',
            header: _t('Scheduled'),
            width: 150,
            sortable: true,
            renderer: renderDate
        },{
            id: 'started',
            dataIndex: 'started',
            header: _t('Started'),
            width: 150,
            sortable: true,
            renderer: renderDate
        },{
            id: 'finished',
            dataIndex: 'finished',
            header: _t('Finished'),
            width: 150,
            sortable: true,
            renderer: renderDate
        }],
        multiSelect: true,
        selectByToken: function(token) {
            var grid = this,
                store = this.getStore(),
                selectToken = function() {
                    var index = store.indexOfId(token),
                        sm = grid.getSelectionModel(),
                        selected = sm.getSelection();
                    if (Ext.isEmpty(selected) || selected[0].get("uuid") != token) {
                        // We linked here, so open the detail
                        Ext.getCmp('job_detail_panel').expand();
                    }
                    grid.getSelectionModel().select(index);
                };
            if (!store.loaded) {
                store.on('load', selectToken, this, {single:true});
            } else {
                selectToken();
            }
        },
        title: _t('Background Jobs'),
        tbar: {
            id: 'jobs-toolbar',
            items: [{
                id: 'deletejob-button',
                iconCls: 'delete',
                text: _t('Delete'),
                tooltip: _t('Delete Jobs'),
                handler: function(btn) {
                    var grid = Ext.getCmp('jobs'),
                    jobids = [];
                    Ext.each(grid.getSelectionModel().getSelection(), function(row) {
                        jobids.push(row.data.uuid);
                    });
                    REMOTE.delete({jobids:jobids}, function() {
                        grid.refresh();
                    });
                }
            },{
                id: 'abortjob-button',
                iconCls: 'suppress',
                text: _t('Abort'),
                tooltip: _t("Abort Jobs"),
                handler: function(btn) {
                    var grid = Ext.getCmp('jobs'),
                    jobids = [];
                    Ext.each(grid.getSelectionModel().getSelection(), function(row) {
                        jobids.push(row.data.uuid);
                    });
                    REMOTE.abort({jobids:jobids}, function() {
                        grid.refresh();
                    });
                }
            },'->',{
                id: 'refreshjobs-button',
                xtype: 'refreshmenu',
                ref: 'refreshmenu',
                stateId: 'jobsrefresh',
                iconCls: 'refresh',
                text: _t('Refresh'),
                tooltip: _t('Refresh Job List'),
                handler: function(btn) {
                    var grid = Ext.getCmp('jobs');
                    grid.refresh();
                }
            }]
        },
        listeners: {
            selectionchange: function(grid, selected) {
                var detail_panel = Ext.getCmp('job_detail_panel');
                if (selected.length==1) {
                    detail_panel.setJob.call(detail_panel, selected[0]);
                    Ext.History.add('jobs:' + selected[0].data.uuid);
                } else {
                    detail_panel.update('');
                    try {
                        detail_panel.updateTask.cancel();
                    } catch (e) {
                        // Nothing
                    }
                }
            },
            itemdblclick: function(grid, item) {
                var detail_panel = Ext.getCmp('job_detail_panel');
                detail_panel.expand();
            }
        },
        showGridPanel: function() {
            var grid = Ext.getCmp('jobs');
        }
    },{
        id: 'job_detail_panel',
        title: _t('Job Log'),
        region: 'south',
        split: true,
        collapsible: true,
        collapsed: true,
        collapseMode: 'mini',
        stateful: false,
        height: 400,
        autoScroll: true,
        updateTask: null,
        bodyStyle: 'padding:8px;background:#fff',
        listeners: {
            expand: function(panel) {
                panel.poll();
            },
            collapse: function(panel) {
                try {
                    panel.updateTask.cancel();
                } catch (e) {
                    // pass
                }
            }
        },
        refresh: function() {
            if (this.job == null) return;
            REMOTE.detail({jobid:this.jobid}, function(r){
                var html = "<b>Log file: " + r.logfile + "</b><br/><br/>";
                for (var i=0; i < r.content.length; i++) {
                    var color = i%2 ? '#b58900' : '#657B83';
                    html += "<pre style='font-family:Monaco,monospaced;font-size:12px;color:" + 
                        color + ";'>" + r.content[i] + '</pre>';
                }
                this.update(html);
                var d = this.body.dom;
                d.scrollTop = d.scrollHeight - d.offsetHeight + 16;
            }, this);
        },
        poll: function() {
            if (!this.collapsed) {
                if (!this.updateTask) {
                    this.updateTask = new Ext.util.DelayedTask(this.poll, this);
                }
                this.refresh();
                var status = this.job.get('status');
                switch (status) {
                    case "STARTED":
                    case "PENDING":
                        this.updateTask.delay(1000);
                        break;
                    case "ABORTED":
                        // Might have updates but only a couple, so let's not
                        // spam the server with requests on a dead job
                        this.updateTask.delay(5000);
                        break;
                }
            }
        },
        setJob: function(job) {
            this.job = job;
            this.jobid = job.get('uuid');
            this.poll();
        }
    }]
});

});
