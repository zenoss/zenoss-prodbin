Ext.ns('Zenoss');

function buildNodeText(node) {
    var b = [];
    var t = node.attributes.text;
    if (node.isLeaf()) {
        b.push(t.text);
    } else {
        b.push('<strong>' + t.text + '</strong>');
    }
    if (t.count!=undefined) {
        b.push('<span class="node-extra">(' + t.count);
        b.push((t.description || 'instances') + ')</span>');
    }
    return b.join(' ');
}

/**
 * @class Zenoss.HierarchyTreePanel
 * @extends Ext.tree.TreePanel
 * The primary way of navigating one or more hierarchical structures. A
 * more advanced Subsections Tree Panel. Configurable as a drop target.
 * Accepts array containing one or more trees (as nested arrays). In at
 * least one case data needs to be asynchronous. Used on screens:
 *   Device Classification Setup Screen
 *   Devices
 *   Device
 *   Event Classification
 *   Templates
 *   Manufacturers
 *   Processes
 *   Services
 *   Report List
 * @constructor
 */

Zenoss.HierarchyTreeNodeUI = Ext.extend(Ext.tree.TreeNodeUI, {
    render: function(bulkRender) {
        var n = this.node,
            a = n.attributes;
        if (a.text && Ext.isObject(a.text)) {
            n.text = buildNodeText(this.node);
        }
        Zenoss.HierarchyTreeNodeUI.superclass.render.call(this, bulkRender);
    },
    onTextChange : function(node, text, oldText){
        if(this.rendered){
            this.textNode.innerHTML = buildNodeText(node);
        }
    }
});

Zenoss.HierarchyTreePanel = Ext.extend(Ext.tree.TreePanel, {
    constructor: function(config) {
        Ext.apply(config, {
            cls: 'hierarchy-panel',
            useArrows: true,
            border: false,
            autoScroll: true,
            containerScroll: true
        });
        if (config.directFn && !config.loader) {
            config.loader = {
                xtype: 'treeloader',
                directFn: config.directFn,
                uiProviders: {
                    'hierarchy': Zenoss.HierarchyTreeNodeUI
                }
            };
            Ext.destroyMembers(config, 'directFn');
        }
        if (config.root && Ext.isString(config.root)) {
            config.root = {
                nodeType: 'async',
                id: config.root,
                uid: config.rootuid,
                text: _t(config.root)
            };
        }
        config.loader.baseAttrs = {iconCls:'severity-icon-small clear'};
        Zenoss.HierarchyTreePanel.superclass.constructor.apply(this,
            arguments);
    },
    initEvents: function() {
        Zenoss.HierarchyTreePanel.superclass.initEvents.call(this);
        this.on('click', function(node, event) {
            Ext.History.add(
                this.id + Ext.History.DELIMITER + node.getPath()
            );
        }, this);
    },
    selectByPath: function(escapedId) {
        var id = unescape(escapedId);
        this.expandPath(id, 'id', function(t, n){
            if (n && !n.isSelected()) {
                n.fireEvent('click', n);
            }
        });
    },
    selectByToken: function(token) {
        if (!this.root.loaded) {
            this.loader.on('load',function(){this.selectByPath(token)}, this);
        } else {
            this.selectByPath(token);
        }
    },
    afterRender: function() {
        Zenoss.HierarchyTreePanel.superclass.afterRender.call(this);
        this.root.ui.addClass('hierarchy-root');
        Ext.removeNode(this.root.ui.getIconEl());
        if (this.searchField) {
            this.filter = new Ext.tree.TreeFilter(this, {
                clearBlank: true,
                autoClear: true
            });
            this.searchField = this.add({
                xtype: 'searchfield',
                bodyStyle: {padding: 10},
                listeners: {
                    valid: this.filterTree,
                    scope: this
                }
            });
        }
        this.getRootNode().expand();
    },
    filterTree: function(e) {
        var text = e.getValue();
        if (this.hiddenPkgs) {
            Ext.each(this.hiddenPkgs, function(n){n.ui.show()});
        }
        this.hiddenPkgs = [];
        if (!text) {
            this.filter.clear();
            return;
        }
        this.expandAll();
        var re = new RegExp(Ext.escapeRe(text), 'i');
        this.filter.filterBy(function(n){
            var match = false;
            Ext.each(n.id.split('/'), function(s){
                match = match || re.test(s);
            });
            return !n.isLeaf() || match;
        });
        this.root.cascade(function(n){
            if(!n.isLeaf() && n.ui.ctNode.offsetHeight<3){
                n.ui.hide();
                this.hiddenPkgs.push(n);
            }
        }, this);
    }
}); // HierarchyTreePanel

Ext.reg('HierarchyTreePanel', Zenoss.HierarchyTreePanel);
