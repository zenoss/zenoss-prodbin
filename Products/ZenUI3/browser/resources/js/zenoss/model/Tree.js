(function() {
    /*
      ###########################################################################
      #
      # This program is part of Zenoss Core, an open source monitoring platform.
      # Copyright (C) 2012, Zenoss Inc.
      #
      # This program is free software; you can redistribute it and/or modify it
      # under the terms of the GNU General Public License version 2 or (at your
      # option) any later version as published by the Free Software Foundation.
      #
      # For complete information please visit: http://www.zenoss.com/oss/
      #
      ###########################################################################
    */

    Ext.ns('Zenoss.model');

    // Common fields used by all tree models
    Zenoss.model.BASE_TREE_FIELDS = [
        {
            name: 'hidden',
            type: 'boolean'
        },
        {
            name: 'leaf',
            type: 'boolean'
        },
        {
            name: 'uid',
            type: 'string'
        },
        {
            name: 'text',
            type: 'object'
        },
        {
            name: 'id',
            type: 'string'
        },
        {
            name: 'path',
            type: 'string'
        },
        {
            name: 'iconCls',
            type: 'string'
        },
        {
            name: 'uuid',
            type: 'string'
        }
    ];

    // A model defined which uses the default tree fields
    Ext.define("Zenoss.model.Tree", {
        extend: 'Ext.data.Model',
        fields: Zenoss.model.BASE_TREE_FIELDS
    });
}());