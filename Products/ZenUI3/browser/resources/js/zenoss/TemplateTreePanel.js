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

Ext.ns('Zenoss');

/**
 * @class Zenoss.TemplateTreePanel
 * @extends Ext.tree.TreePanel
 * @constructor
 */
Zenoss.TemplateTreePanel = Ext.extend(Zenoss.HierarchyTreePanel, {

    constructor: function(config) {
        Ext.applyIf(config, {
            root: new Ext.tree.AsyncTreeNode({
                
            })
        });
        Zenoss.TemplateTreePanel.superclass.constructor.call(this, config);
    }

});

Ext.reg('TemplateTreePanel', Zenoss.TemplateTreePanel);

})();
