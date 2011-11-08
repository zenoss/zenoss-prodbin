/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
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

Ext.define("Zenoss.CommandPanel", {
    alias:['widget.commandpanel'],
    extend:"Zenoss.IFramePanel",
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            ignoreClassName: true,
            autoEl: {
                tag: 'iframe allowtransparency="true"',
                id: Ext.id(),
                src: config.url || '',
                frameborder: 0
            }
        });
        Zenoss.CommandPanel.superclass.constructor.call(this, config);
        this.on('frameload', this.injectForm, this, {single:true});
    },
    injectForm: function(win){
        var doc = this.getDocument(),
            form = formTpl.apply({
                data: Ext.encode(this.data),
                target: this.target
            });
        this.getBody().innerHTML = form;
        doc.commandform.submit();
        this.parentWindow.setSize(this.parentWindow.getSize());
    }
});



/**********************************************************************
 *
 *  Command Window
 *
 */
Ext.define("Zenoss.CommandWindow", {
    alias:['widget.commandwindow'],
    extend:"Ext.Window",
    constructor: function(config) {
        this.cpanel = Ext.id();
        this.commandData = config.data ||
            { uids: config.uids, command: config.command };
        this.target = config.target;
        if (Ext.isDefined(config.redirectTarget)) {
            config.closeAction = 'closeAndRedirect';
            this.redirectTarget = config.redirectTarget;
        }
        config = Ext.applyIf(config || {}, {
            layout: 'fit',
            title: config.command || config.title,
            cls: 'streaming-window',
            constrain: true,
            closable:true,
            plain: true,
            items: {
                id: this.cpanel,
                xtype: config.panel || 'commandpanel', //default to commandpanel
                data: this.commandData,
                target: config.target,
                autoLoad: config.autoLoad,
                parentWindow: this
            },
            fbar: {
                buttonAlign: 'left',
                id:'window_footer_toolbar',
                items: {
                    xtype: 'checkbox',
                    checked: true,
                    boxLabel: '<span style="color:white">Autoscroll</span>',
                    handler: Ext.bind(function(c){
                        if (c.checked) {
                            this.startScrolling();
                        } else {
                            this.stopScrolling();
                        }
                    }, this)
                }
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
        if (Ext.isString(this.cpanel)) {
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
        } catch(e) {
            Ext.emptyFn();
        }
        this.task.delay(250);
        Ext.get('window_footer_toolbar').focus();        
    },
    closeAndReload: function() { 
        (function() {window.top.location.reload();}).defer(1, this);
        this.destroy();
    },
    closeAndRedirect: function() {
        this.on('close', function() {
            (function() {
                window.top.location = this.redirectTarget;
            }).defer(1, this);
        });
        this.destroy();
    }
});



})();
