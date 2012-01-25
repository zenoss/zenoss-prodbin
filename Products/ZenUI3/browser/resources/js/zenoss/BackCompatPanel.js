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

Ext.define("Zenoss.IFramePanel", {
    alias:['widget.iframe'],
    extend:"Ext.Component",
    frameLoaded: false,
    testEarlyReadiness: false,
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            timeout: 5000, // Wait 5s for iframe to initialize before failing
            pollInterval: 50,
            ignoreClassName: false,
            autoEl: {
                tag: 'iframe',
                id: Ext.id(),
                src: config.url || '',
                frameborder: 0
            }
        });
        Zenoss.IFramePanel.superclass.constructor.call(this, config);
        this.addEvents('frameload', 'framefailed', 'isReady');
        this.on('frameload', function(win) {
            // Load any messages that may have been created by the frame
            Zenoss.messenger.checkMessages();
        }, this);
    },
    onRender: function(ct, position) {
        Zenoss.IFramePanel.superclass.onRender.apply(this, arguments);
        // Hook up load events
        this.frame = this.getEl();
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
        var doc = this.getDocument(),
            currentUrl = doc ? doc.location.href : null,
            ready = false,
            readyTooEarly = this.testEarlyReadiness,
            body, dom, href,
            i = 0,
            timestocheck = this.timeout / this.pollInterval;
        Ext.bind(function do_check() {
            if (this.frameLoaded) {
                return;
            }
            body = this.getBody();
            if (currentUrl == 'about:blank' || currentUrl == '') {
                // if an iframe is reused, it could have a body and
                // className immediately, but not the desired ones.
                // in that case, poll until the ready test fails,
                // then again until it succeeds.
                if (readyTooEarly) {
                    readyTooEarly = !!body
                            && (this.ignoreClassName || !!body.className);
                } else {
                    ready = !!body
                            && (this.ignoreClassName || !!body.className);

                    // Allow subclasses and clients defined when the panel is ready
                    ready = ready && this.fireEvent('isReady', this.getWindow());
                }
            } else {
                dom = body ? body.dom : null;
                href = this.getDocument().location.href;
                ready = href != currentUrl || (dom && dom.innerHTML);

                // Allow subclasses and clients defined when the panel is ready
                ready = ready && this.fireEvent('isReady', this.getWindow());
            }
            if (ready  || i++ > timestocheck) {
                this.frameLoaded = ready;
                    this.fireEvent(ready ? 'frameload' : 'framefailed',
                               this.getWindow());
            } else {
                Ext.defer(do_check, this.pollInterval, this);
            }
        }, this)();
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
        return this.frame.dom.contentWindow
                || window.frames[this.frame.dom.name];
    },
    setSrc: function(url) {
        this.frameLoaded = false;
        if (url == 'about:blank' || url == '') {
            this.frame.dom.src = url;
        } else {
            this.frame.dom.src = Ext.urlAppend(url,
                    '_dc=' + new Date().getTime());
        }
        this.waitForLoad();
    }
});




/**
 * Panel used for displaying old zenoss ui pages in an iframe. Set Context
 * should be called by page to initialze panel for viewing.
 *
 * @class Zenoss.BackCompatPanel
 * @extends Zenoss.ContextualIFrame
 */
Ext.define("Zenoss.BackCompatPanel", {
    alias:['widget.backcompat'],
    extend:"Zenoss.IFramePanel",
    contextUid: null,
    constructor: function(config) {
        Ext.apply(config || {}, {
            testEarlyReadiness: true
        });
        Zenoss.BackCompatPanel.superclass.constructor.call(this, config);
        this.addEvents('frameloadfinished');
        this.on('frameload', function(win) {
            if (Ext.isDefined(win.Ext) && Ext.isDefined(win.Ext.onReady)) {
                var me = this;
                win.Ext.onReady(function(){
                    me.fireEvent('frameloadfinished', win);
                });
            }else if (win.document && win.document.body) {
                this.fireEvent('frameloadfinished', win);
            } else {
                win.onload = Ext.bind(function() {
                    this.fireEvent('frameloadfinished', win);
                }, this);
            }
        }, this);

        // the frame is not finished loading until Ext is ready
        this.on('isReady', function(win){
            return Ext.isDefined(win.Ext) && Ext.isDefined(win.Ext.onReady);
        });
    },
    setContext: function(uid) {
        this.contextUid = uid;
        var url = uid;
        if (Ext.isDefined(this.viewName) && this.viewName !== null) {
            url = uid + '/' + this.viewName;
        }
        this.setSrc(url);
    }
});





Zenoss.util.registerBackCompatMenu = function(menu, btn, align, offsets){

    align = align || 'bl';
    offsets = offsets || [0, 0];

    var layer = new Ext.Panel({
        floating: true,
        contentEl: menu,
        border: false,
        shadow: !Ext.isIE,
        bodyCls: menu.id=='contextmenu_items' ? 'z-bc-z-menu z-bc-page-menu' : 'z-bc-z-menu'
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
    btn.on('click', function(){
        btn.fireEvent('menushow', btn, btn.menu);
    });
    btn.on('menushow', showMenu);
    btn.on('menuhide', hideMenu);
    menu.on('mousedown', menuClicked);

};

})();
