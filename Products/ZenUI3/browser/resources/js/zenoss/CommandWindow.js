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

Zenoss.CommandPanel = Ext.extend(Zenoss.IFramePanel, {
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
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
        var doc = win.document,
            form = formTpl.apply({
                data: Ext.encode(this.data),
                target: this.target
            });
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
        this.commandData = config.data ||
            { uids: config.uids, command: config.command };
        this.target = config.target;
        config = Ext.applyIf(config || {}, {
            layout: 'fit',
            title: config.command || config.title,
            cls: 'streaming-window',
            constrain: true,
            plain: true,
            items: {
                border: false,
                id: this.cpanel,
                // default to command panel
                xtype: config.panel || 'commandpanel',
                data: this.commandData,
                target: config.target,
                autoLoad: config.autoLoad,
                parentWindow: this
            }
        });
        var fbarItems = [];
        if (config.redirectTarget) {
            fbarItems.push({
                xtype: 'button',
                text: _t('Done'),
                handler: function(c){
                    window.location = config.redirectTarget;
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
    },
    show: function() {
        if (Ext.isWebKit) {
            var url = 'no_streaming=1&data=';
            url += Ext.encode(this.commandData);
            if (this.commandData.command) {
                url += "&command=";
                url += this.commandData.command;
            }
            window.open(this.target + '?'+ url,'',
            'width=800,height=500,toolbar=0,location=0,directories=0,menubar=0,resizable=1,scrollbars=1');
        } else {
            Zenoss.CommandWindow.superclass.show.apply(this);
        }
    }
});

Ext.reg('commandwindow', Zenoss.CommandWindow);

})();
