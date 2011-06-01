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

Zenoss.IFramePanel = Ext.extend(Ext.BoxComponent, {
    frameLoaded: false,
    frameSrc: '',
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            timeout: 5000, // Wait 5 seconds for iframe to initialize before failing
            autoEl: {
                tag: 'iframe',
                id: Ext.id(),
                src: config.url || '',
                frameborder: 0
            }
        });
        this.frameSrc = config.src;
        Zenoss.IFramePanel.superclass.constructor.call(this, config);
    },
    initEvents: function() {
        Zenoss.IFramePanel.superclass.initEvents.call(this);
        this.addEvents('frameload', 'framefailed');
        this.on('frameload', function(win) {
            // Load any messages that may have been created by the frame
            Zenoss.messenger.checkMessages();
        }, this);
    },
    onRender: function(ct, position) {
        Zenoss.IFramePanel.superclass.onRender.apply(this, arguments);
        // Hook up load events
        this.frame = this.getEl();
        this.frameParent = this.frame.findParent('div.x-panel-body', null, true);
        this.waitForLoad();
    },
    afterRender: function(container) {
        Zenoss.IFramePanel.superclass.afterRender.apply(this, arguments);
        if (!this.ownerCt) {
            var pos = this.getPosition(),
                size = this.frame.parent().getViewSize();
            this.setSize(size.width - pos[0], size.height-pos[1]);
        }
    },
    waitForLoad: function() {
        var b, i = 0,
            ready = false,
            timestocheck = this.timeout / 5, // Because we poll every 5ms
            doc = this.getDocument(),
            currentUrl = doc ? doc.location.href : null;
        (function do_check() {
            var document = this.getDocument();
            if (this.frameLoaded) {
                return;
            }
            if (currentUrl == 'about:blank' || currentUrl == '') {
                ready = !!this.getBody();
            } else {
                ready = ((document.location.href != currentUrl || document.location.href === this.frameSrc)
                        && ((b = this.getBody()) && !!(b.dom.innerHTML || '').length))
                        || false;
            }
            if (!ready && i++ < timestocheck) {
                // Schedule the next check
                do_check.defer(5, this);
                return;
            }
            if (ready) {
                this.frameLoaded = true;
                this.fireEvent('frameload', this.getWindow());
            } else {
                this.fireEvent('framefailed', this.getWindow());
            }
        }).createDelegate(this)();
    },
    getBody: function() {
        var doc = this.getDocument();
        return doc.body || doc.documentElement;
    },
    getDocument: function() {
        var window = this.getWindow();
        return (Ext.isIE && window ? window.document : null) ||
                this.frame.dom.contentDocument ||
                window.frames[this.frame.dom.name].document ||
                null;
    },
    getWindow: function() {
        return this.frame.dom.contentWindow || window.frames[this.frame.dom.name];
    },
    setSrc: function(url) {
        this.frameLoaded = false;
        this.frame.dom.src = this.frameSrc = url;
        this.waitForLoad();
    }
});

Ext.reg('iframe', Zenoss.IFramePanel);


Zenoss.ContextualIFrame = Ext.extend(Zenoss.IFramePanel, {
    contextUid: null,
    refreshOnContextChange: false,
    setContext: function(uid) {
        if (this.refreshOnContextChange || this.contextUid!=uid) {
            this.contextUid = uid;
            var url = uid;
            if (Ext.isDefined(this.viewName) && this.viewName !== null) {
                url = uid + '/' + this.viewName;
            }
            this.setSrc(url);
        }
    }
});

Ext.reg('contextiframe', Zenoss.ContextualIFrame);

/**
 * Panel used for displaying old zenoss ui pages in an iframe. Set Context
 * should be called by page to initialze panel for viewing.
 *
 * NOTE: sets a cookie named "newui"; the presence of this cookie will cause the
 * old ui to render with out the old navigation panels and without the tabs.
 *
 * @class Zenoss.BackCompatPanel
 * @extends Zenoss.ContextualIFrame
 */
Zenoss.BackCompatPanel = Ext.extend(Zenoss.ContextualIFrame, {
    setContext: function(uid) {
        Ext.util.Cookies.set('newui', 'yes');
        Zenoss.BackCompatPanel.superclass.setContext.apply(this, arguments);
        this.on('frameload', function(win){
            if (win.document && win.document.body) {
                win.document.body.className = win.document.body.className + ' z-bc';
            } else {
                win.onload = function() {
                    win.document.body.className = win.document.body.className + ' z-bc';
                };
            }
        });
    }
});

Ext.reg('backcompat', Zenoss.BackCompatPanel);



Zenoss.util.registerBackCompatMenu = function(menu, btn, align, offsets){

    align = align || 'bl';
    offsets = offsets || [0, 0];

    var layer = new Ext.Panel({
        floating: true,
        contentEl: menu,
        border: false,
        shadow: !Ext.isIE,
        bodyCssClass: menu.id=='contextmenu_items' ? 'z-bc-z-menu z-bc-page-menu' : 'z-bc-z-menu'
    });

    layer.render(Ext.getBody());

    function showMenu() {
        var xy = layer.getEl().getAlignToXY(btn.getEl(), align, offsets);
        layer.setPagePosition(xy[0], xy[1]);
        menu.dom.style.display = 'block';
        layer.show();
    }

    function hideMenu() {
        layer.hide();
    }

    function menuClicked(e) {
        var link = e.getTarget('a');
        if (link) {
            // Fake a click
            location.href = link.href;
        }
    }

    btn.on('menushow', showMenu);
    btn.on('menuhide', hideMenu);
    menu.on('mousedown', menuClicked);

};

})();
