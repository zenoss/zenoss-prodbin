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

Zenoss.IFramePanel = Ext.extend(Ext.BoxComponent, {
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            autoEl: {
                tag: 'iframe',
                id: Ext.id(),
                src: config.url || '',
                frameborder: 0
            }
        });
        Zenoss.IFramePanel.superclass.constructor.call(this, config);
    },
    initEvents: function() {
        Zenoss.IFramePanel.superclass.initEvents.call(this);
        this.addEvents('frameload');
    },
    onRender: function(ct, position) {
        Zenoss.IFramePanel.superclass.onRender.apply(this, arguments);
        // Hook up load events
        this.frame = this.getEl();
        this.frameParent = this.frame.findParent('div.x-panel-body', null, true);
        var evname = Ext.isIE?'onreadystatechange':'onload';
        this.frame.dom[evname] = this.onFrameLoad.createDelegate(this);
    },
    afterRender: function(container) {
        Zenoss.IFramePanel.superclass.afterRender.apply(this, arguments);
        if (!this.ownerCt) {
            var pos = this.getPosition(), 
                size = this.frame.parent().getViewSize();
            this.setSize(size.width - pos[0], size.height-pos[1]);
        }
    },
    getWindow: function() {
        return this.frame.dom.contentWindow || window.frames[this.frame.dom.name];
    },
    setSrc: function(url) {
        this.frame.dom.src = url;
    },
    onFrameLoad: function() {
        this.fireEvent('frameload', this.getWindow());
    }
});

Ext.reg('iframe', Zenoss.IFramePanel);


Zenoss.ContextualIFrame = Ext.extend(Zenoss.IFramePanel, {
    contextUid: null,
    setContext: function(uid) {
        if (this.contextUid!=uid) {
            this.contextUid = uid;
            var url = uid + '/' + this.viewName;
            this.setSrc(url);
        }
    }
});

Ext.reg('contextiframe', Zenoss.ContextualIFrame);


Zenoss.BackCompatPanel = Ext.extend(Zenoss.ContextualIFrame, {
    setContext: function(uid) {
        if (this.contextUid!=uid){
            this.on('frameload', this.injectViewport, {scope:this, single:true});
        }
        Zenoss.BackCompatPanel.superclass.setContext.apply(this, arguments);
    },
    injectViewport: function(win) {
        var doc = win.document,
            script = doc.createElement('script'),
            code = "new Ext.Viewport({layout:'fit', items:[{contentEl:'contentPane'}]}).doLayout();";

        script.type = 'text/javascript';
        script.text = code;

        doc.body.appendChild(script);
    }
});

Ext.reg('backcompat', Zenoss.BackCompatPanel);


})();
