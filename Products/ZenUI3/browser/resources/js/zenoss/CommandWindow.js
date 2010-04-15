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

(function(){
     
/**********************************************************************
 *
 * Command Panel 
 *
 */
var formTpl = new Ext.Template(
    '<form name="commandform" method="POST" action="{target}">',
    '<textarea style="visibility:hidden" name="data">',
    '{data}',
    '</textarea>',
    '</form>');
formTpl.compile();

Zenoss.CommandPanel = Ext.extend(Zenoss.IFramePanel, {
    constructor: function(config) {
        Zenoss.CommandPanel.superclass.constructor.call(this, config);
        this.on('frameload', this.injectForm, this, {single:true});
    },
    injectForm: function(win){
        var doc = win.document,
            data = {uids: this.uids, command: this.command},
            form = formTpl.apply({
                data: Ext.encode(data), 
                target: this.target + '/run_command'
            });
        doc.body.innerHTML = form;
        doc.commandform.submit();
        this.parentWindow.setSize(this.parentWindow.getSize());
    }
});

Ext.reg('commandpanel', Zenoss.CommandPanel);

Zenoss.BackupPanel = Ext.extend(Zenoss.CommandPanel, {
    injectForm: function(win){
        var doc = win.document,
            data = {args: this.args, command: this.command},
            form = formTpl.apply({
                data: Ext.encode(data), 
                target: '/run_backup'
            });
        doc.body.innerHTML = form;
        doc.commandform.submit();
        this.parentWindow.setSize(this.parentWindow.getSize());
    }
});

Ext.reg('backuppanel', Zenoss.BackupPanel);

/**********************************************************************
 *
 *  Command Window
 *
 */  
Zenoss.CommandWindow = Ext.extend(Ext.Window, {
    constructor: function(config) {
        this.cpanel = Ext.id();
        config = Ext.applyIf(config || {}, {
            layout: 'fit',
            title: config.command,
            redirectButton: config.redirectButton || false,
            cls: 'streaming-window',
            constrain: true,
            plain: true,
            items: {
                border: false,
                id: this.cpanel,
                // default to command panel
                xtype: config.panel || 'commandpanel',
                uids: config.uids,
                args: config.args,
                target: config.target,
                command: config.command,
                autoLoad: config.autoLoad,
                parentWindow: this
            }
        });
        var fbarItems = [];
        if (config.redirectButton) {
            fbarItems.push({
                xtype: 'button',
                text: _t('See Changes'),
                handler: function(c){
                    window.location = window.location;
                }.createDelegate(this)
            });
        }
        fbarItems.push({
            xtype: 'checkbox',
            checked: true,
            boxLabel: '<span style="color:white">Autoscroll</span>',
            handler: function(c){
                if (c.checked) {
                    this.startScrolling();
                } else {
                    this.stopScrolling();
                }
            }.createDelegate(this)
        });
        config = Ext.applyIf(config, {
            fbar: {
                items: fbarItems
            }
        });
        Zenoss.CommandWindow.superclass.constructor.call(this, config);
        this.task = new Ext.util.DelayedTask(this.scrollToBottom, this);
        this.on('render', this.startScrolling, this);
        this.on('afterlayout', function(){this.center();}, this, {single:true});
    },
    onRender: function() {
        Zenoss.CommandWindow.superclass.onRender.apply(this, arguments);
        var vsize = Ext.getBody().getViewSize();
        this.setSize({width:vsize.width*0.95, height:vsize.height*0.95});
    },
    getCommandPanel: function() {
        if(Ext.isString(this.cpanel)) {
            this.cpanel = Ext.getCmp(this.cpanel);
        }
        return this.cpanel;
    },
    startScrolling: function() {
        this.task.delay(250);
    },
    stopScrolling: function() {
        this.task.cancel();
    },
    scrollToBottom: function() {
        try {
            var win = this.getCommandPanel().getWindow(),
                body = win.document.body;
            Zenoss.env.BODY = body;
            win.scrollBy(0, body.scrollHeight);
        } catch(e) { Ext.emptyFn(); }
        this.task.delay(250);
    }
});

Ext.reg('commandwindow', Zenoss.CommandWindow);

})();
