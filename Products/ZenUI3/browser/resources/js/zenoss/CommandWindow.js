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
    '<form name="commandform" method="POST" action="{target}/run_command">',
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
            form = formTpl.apply({data:Ext.encode(data), target:this.target});
        doc.body.innerHTML = form;
        doc.commandform.submit();
        this.parentWindow.setSize(this.parentWindow.getSize());
    }
});

Ext.reg('commandpanel', Zenoss.CommandPanel);

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
            cls: 'streaming-window',
            constrain: true,
            plain: true,
            fbar: {
                items:[{
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
                }]
            },
            items: {
                border: false,
                id: this.cpanel,
                // default to command panel
                xtype: config.panel || 'commandpanel',
                uids: config.uids,
                target: config.target,
                command: config.command,
                autoLoad: config.autoLoad,
                parentWindow: this
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
