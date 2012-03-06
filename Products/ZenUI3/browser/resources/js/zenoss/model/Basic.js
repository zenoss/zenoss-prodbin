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

    /**
     * Model that defines a uid and name
     **/
    Ext.define("Zenoss.model.Basic", {
        extend: 'Ext.data.Model',
        idProperty: 'uid',
        fields: ['uid', 'name']
    });
    
    /**
     * Model that defines a uid and label
     **/
    Ext.define("Zenoss.model.Label", {
        extend: 'Ext.data.Model',
        idProperty: 'uid',
        fields: ['uid', 'label']
    });    

    /**
     * Like the basic model but defined with the UUID instead of the uid
     **/
    Ext.define("Zenoss.model.BasicUUID", {
        extend: 'Ext.data.Model',
        idProperty: 'uuid',
        fields: ['uuid', 'name']
    });

    /**
     * Store that just defines a name
     **/
    Ext.define("Zenoss.model.Name", {
        extend: 'Ext.data.Model',
        idProperty: 'name',
        fields: ['name']
    });

    Ext.define("Zenoss.model.NameValue", {
        extend: 'Ext.data.Model',
        idProperty: 'value',
        fields: ['name', 'value']
    });

    Ext.define("Zenoss.model.IdName", {
        extend: 'Ext.data.Model',
        idProperty: 'id',
        fields: ['id', 'name']
    });

    Ext.define("Zenoss.model.ValueText", {
        extend: 'Ext.data.Model',
        idProperty: 'value',
        fields: ['value', 'text']
    });

}());
