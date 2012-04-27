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
(function () {

Ext.ns('Zenoss');

var REMOTE = Zenoss.remote.JobsRouter;

function lengthOrZero(o) {
    return o==null ? 0 : o.length;
}

function isObjectEmpty(o) {
    for (var i in o) {
        if (o.hasOwnProperty(i)) {
             return false;
        }
    }
    return true;
}

function jobLinkRenderer(value, metadata, record) {
    var job = record.data,
        description = job.description;
    description = description.length > 58 ? description.substring(0, 55) + '...' : description;
    return "<a href='/zport/dmd/joblist#jobs:" + job.uuid + "'>" + description + "</a>";
}

function readableRenderer(value, metadata, record) {
    var adjective,
        job = record.data,
        secondsdiff = new Date().getTimezoneOffset() * 60,
        date = new Date(0);
    switch (job.status) {
        case "SUCCESS":
            adjective = _t("Finished");
            break;
        case "STARTED":
            adjective = _t("Started");
            break;
        case "PENDING":
            adjective = _t("Scheduled");
            break;
    }
    date.setUTCSeconds(value - secondsdiff);
    return adjective + " " + date.readable(1);
}

Ext.define("Zenoss.model.Job", {
    extend: 'Ext.data.Model',
    idProperty: 'uuid',
    fields: [
        'uuid', 
        'type', 
        'description', 
        'scheduled',
        'started', 
        'finished',
        'status', 
        'result'
    ]
});

var runningJobsStore = Ext.create('Ext.data.Store', {
    model: 'Zenoss.model.Job',
    initialSortColumn: 'running'
});

var pendingJobsStore = Ext.create('Ext.data.Store', {
    model: 'Zenoss.model.Job',
    initialSortColumn: 'pending'
});

var finishedJobsStore = Ext.create('Ext.data.Store', {
    model: 'Zenoss.model.Job',
    initialSortColumn: 'finished'
});

Ext.define("Zenoss.JobsWidget", {
    alias: ['widget.jobswidget'],
    extend: "Ext.Button",
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            stateful: true,
            stateEvents: 'update', 
            menuAlign: 'br-tr?',
            menu: {
                layout: 'fit',
                plain: true,
                bodyStyle: 'background:transparent;padding:0;border:0',
                style: 'background:transparent;padding:0;border:0',
                items: [{
                    xtype: 'container',
                    width: 425,
                    style: {
                        border: '1px solid #444',
                        '-webkit-border-radius': 5,
                        '-moz-border-radius': 5,
                        '-ms-border-radius': 5,
                        borderRadius: 5
                    },
                    items: [{
                        id: 'nojobspanel',
                        xtype: 'panel',
                        bodyStyle: 'padding:4px',
                        hidden: true,
                        html: _t('No jobs')
                    },{
                        id: 'jobs-grid-running',
                        xtype: 'grid',
                        hideHeaders: true,
                        forceFit: true,
                        stateful: false,
                        disableSelection: true,
                        title: _t('Running jobs'),
                        store: runningJobsStore,
                        columns: [{
                            header: 'description', 
                            dataIndex: 'description', 
                            renderer: jobLinkRenderer
                        }, {
                            header: 'started', 
                            dataIndex: 'started', 
                            renderer: readableRenderer,
                            width: 150
                        }]
                    },{
                        id: 'jobs-grid-pending',
                        xtype: 'grid',
                        hideHeaders: true,
                        forceFit: true,
                        stateful: false,
                        disableSelection: true,
                        title: _t('Pending jobs'),
                        store: pendingJobsStore,
                        columns: [{
                            header: 'description', 
                            dataIndex: 'description', 
                            renderer: jobLinkRenderer
                        }, {
                            header: 'scheduled', 
                            dataIndex: 'scheduled', 
                            renderer: readableRenderer,
                            width: 150
                        }]
                    },{
                        id: 'jobs-grid-finished',
                        xtype: 'grid',
                        hideHeaders: true,
                        forceFit: true,
                        stateful: false,
                        disableSelection: true,
                        title: _t('Finished jobs'),
                        store: finishedJobsStore,
                        columns: [{
                            header: 'description', 
                            dataIndex: 'description', 
                            renderer: jobLinkRenderer,
                            flex: 1
                        }, {
                            header: 'finished', 
                            dataIndex: 'finished', 
                            renderer: readableRenderer,
                            width: 150
                        }]
                    },{
                        xtype: 'panel',
                        id: 'more-jobs-link',
                        bodyStyle: 'font-size:11px; padding:3px; padding-left: 5px',
                        html: '<a href="/zport/dmd/joblist">More...</a>'
                    }]
                }]
            }
        });
        this.lastchecked = 0;
        this.callParent([config]);
        this.on('render', this.on_render, this, {single:true});
        this.pollTask = new Ext.util.DelayedTask(this.poll, this);
    },
    on_render: function() {
        this.menucontainer = this.menu.items.items[0];
        this.init_tip();
        this.poll();
    },
    initEvents: function() {
        this.callParent(arguments);
        this.addEvents('update');
        // Listen to Direct requests for job results
        Ext.Direct.on('event', function(e) {
            if (Ext.isDefined(e.result) && e.result && Ext.isDefined(e.result.new_jobs)) {
                Ext.each(e.result.new_jobs, function(job) {
                    this.alert_new(job);
                }, this); 
            }
        }, this);
    },
    getState: function() {
        return {'lastchecked':this.lastchecked};
    },
    applyState: function(state) {
        this.lastchecked = state.lastchecked;
    },
    init_tip: function() {
        var me = this,
            klass = Ext.ClassManager.getByAlias("widget.tooltip");
            tip = this.tip = Ext.create('Ext.tip.ToolTip', {
                target: this,
                dismissDelay: 9000,
                show: function() {
                    klass.prototype.show.call(this);
                    this.triggerElement = me.el;
                    this.clearTimer('hide');
                    this.targetXY = this.el.getAlignToXY(me.el, 'br-tr', [-15, -18]);
                    klass.prototype.show.call(this);
                }
            });
        tip.mun(this, 'mouseover', tip.onTargetOver, tip);
        tip.mun(this, 'mouseout', tip.onTargetOut, tip);
        tip.mun(this, 'mousemove', tip.onMouseMove, tip);
    },
    alert: function(msg) {
        if (this.tip.isVisible()) {
            msg = this.tip.body.dom.innerHTML + '<br/><br/>' + msg
        }
        this.tip.update(msg);
        this.tip.show();
    },
    alert_new: function(job) {
        this.alert("<b>New job</b>: " + job.description);
    },
    alert_finished: function(job) {
        this.alert("<b>Finished job</b>: " + job.get('description'));
    },
    poll: function() {
        this.update();
        this.pollTask.delay(5000);
    },
    check_for_recently_finished: function(jobs) {
        if (Ext.isDefined(jobs.SUCCESS)) {
            Ext.each(jobs.SUCCESS, function(job) {
                if (job.get('finished') >= this.lastchecked) {
                    this.alert_finished(job);
                }
            }, this);
        }
        this.set_lastchecked();
    },
    update_button: function(totals) {
        var pending = lengthOrZero(totals.PENDING),
            running = lengthOrZero(totals.STARTED),
            text;
        if (!pending && !running) {
            text = _t("No background jobs");
        } else {
            text = running + " jobs running (" + pending + " pending)";
        }
        this.setText(text);
    },
    add_menu_job: function(job) {
        var adjective,
            relevant_time,
            secondsdiff = new Date().getTimezoneOffset() * 60,
            date = new Date(0);
        switch (job.status) {
            case "SUCCESS":
                adjective = _t("Finished");
                relevant_time = job.finished;
                break;
            case "STARTED":
                adjective = _t("Started");
                relevant_time = job.started;
                break;
            case "PENDING":
                adjective = _t("Scheduled");
                relevant_time = job.scheduled;
                break;
        }
        date.setUTCSeconds(relevant_time - secondsdiff);
        this.menucontainer.add({
            xtype: 'panel',
            width: 425,
            layout: {
                type: 'hbox',
                align: 'stretchmax'
            },
            defaults: {
                style: {
                    padding: 2
                }
            },
            items: [{
                html: job.description.length > 48 ? job.description.substring(0, 45) + '...' : job.description,
                flex: 2
            },{
                html: adjective + " " + date.readable(1),
                flex: 1
            }]
        });
    },
    update_menu: function(jobs) {
        if (!isObjectEmpty(jobs)) {
            Ext.getCmp('nojobspanel').hide();
            Ext.getCmp('jobs-grid-running').setVisible(jobs.STARTED);
            if (jobs.STARTED) {
                runningJobsStore.loadData(jobs.STARTED);
            }
            Ext.getCmp('jobs-grid-pending').setVisible(jobs.PENDING);
            if (jobs.PENDING) {
                pendingJobsStore.loadData(jobs.PENDING);
            }
            Ext.getCmp('jobs-grid-finished').setVisible(jobs.SUCCESS);
            if (jobs.SUCCESS) {
                finishedJobsStore.loadData(jobs.SUCCESS)
            }
            Ext.getCmp('more-jobs-link').show();
        } else {
            Ext.getCmp('nojobspanel').show();
            Ext.getCmp('jobs-grid-running').hide();
            Ext.getCmp('jobs-grid-pending').hide();
            Ext.getCmp('jobs-grid-finished').hide();
            Ext.getCmp('more-jobs-link').hide();
        }
    },
    set_lastchecked: function() {
        var secondsdiff = new Date().getTimezoneOffset()*60;
        this.lastchecked = (new Date().getTime()/1000) + secondsdiff;
        this.fireEvent('update', this);
    },
    update: function() {
        REMOTE.userjobs({}, function(result){
            var jobs = result.jobs;
            this.update_button(result.totals);
            this.update_menu(jobs);
            this.check_for_recently_finished(jobs);
        }, this);
    }
});

})(); // End local namespace
