/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){

    Ext.define('Daemons.model.Daemon', {
        extend: 'Ext.data.Model',
        fields: Zenoss.model.BASE_TREE_FIELDS.concat([
            {name: 'id',  type: 'string'},
            {name: 'uuid',  type: 'string'},
            {name: 'children',  type: 'Array'},
            {name: 'status',  type: 'string'},
            {name: 'enabled',  type: 'boolean'}
        ])
    });

    Ext.define('Daemons.store.Daemons', {
        extend: 'Ext.data.TreeStore',
        model: 'Daemons.model.Daemon',
        data: [
            {id: 'Localhost', uuid: '12', children: [], status: '1', enabled: true}
        ]
    });

})();
