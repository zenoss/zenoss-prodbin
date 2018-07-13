/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


/* package level */
(function() {

Ext.ns('Zenoss.form');

Ext.define("Zenoss.form.LinkField", {
    extend: "Ext.form.DisplayField",
    alias: ['widget.linkfield'],
    initComponent: function() {
        this.callParent(arguments);
        // make sure our value is established
        // before rendering
        this.setValue(this.value);
    },
    getValue: function() {
        return this.rawValue;
    },
    setValue: function(value) {
        var origValue = value;
        if (Ext.isEmpty(value)) {
            value = _t('None');
        } else if (Ext.isObject(value)) {
            value = Zenoss.render.link(null, value.uid, value.name);
        } else if (Ext.isArray(value)) {
            var items = [];
            Ext.each(value, function(v){
                items.push(Zenoss.render.link(v));
            });
            value = items.join('<br/>');
        } else {
            var linkMatch = value.match(/(?:<a href=")(.+)(?:">)/);
            var nameMatch = value.match(/(?:<a href=.*">)(.+)(?:<\/a>)/);
            if (linkMatch && nameMatch) {
                var link = linkMatch[1];
                var name = nameMatch[1];
                value = Zenoss.render.link(null, link, name);
            } else {
                value = Zenoss.render.link(value);
            }
        }
        this.callParent([value]);
        this.rawValue = origValue;
    }
 });


})();
