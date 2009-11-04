/*
 * Module: directstore
 * 
 * Test interaction between directstore and Ext Direct server implementation.
 *
 */

Ext.onReady(function(){
    
    Ext.Direct.addProvider({
        type: 'remoting',
        url: 'http://localhost:7999/directstore',
        namespace: 'Remote',
        actions: {'CrudService': [
            {name: 'create', len:1},
            {name: 'read', len:1},
            {name: 'update', len:1},
            {name: 'destroy', len:1}
        ]} // actions
    }); // addProvider
    
    var baseStoreConfig = {
        root: 'records',
        writer: new Ext.data.JsonWriter({encode: false}),
        api: {
            create: Remote.CrudService.create,
            read: Remote.CrudService.read,
            update: Remote.CrudService.update,
            destroy: Remote.CrudService.destroy
        }, // api
        fields: [
            {name: 'id', type: 'int'},
            {name: 'shape', type: 'string'}, 
            {name: 'color', type: 'string'},
            {name: 'number', type: 'int'}
        ] // fields
    };
    
    
    /* ***********************************************************************
     * Module 1: test a store with the default config options
     *
     */
    (function(){
        
        module('directstore: default config options');
        
        // a store with the defaul config options
        var store = new Ext.data.DirectStore(baseStoreConfig);
        
        store.on('exception', function(misc) {
            ok(false, 'exception: ' + misc);
        });
        
        asyncTest('initial load of empty store', function() {
            expect(1);
            store.load({callback: function(records, options, success){
                equals(records.length, 0, "No records expected on initial load");
                start();
            }});
        }); // initial load
        
        asyncTest('add 3 green ovals', function() {
            expect(1);
            var callback = function(store, action, result, res, record) {
                equals(record.data.id, 0, 'id is 0');
                store.un('write', callback);
                start();
            };
            store.on('write', callback);
            var data = {shape: 'oval', color: 'green', number: 3};
            store.add(new store.recordType(data));
        }); // add 3 green ovals

        asyncTest('add 2 purple diamonds', function() {
            expect(1);
            var callback = function(store, action, result, res, record) {
                equals(record.data.id, 1, 'id is 1');
                store.un('write', callback);
                start();
            };
            store.on('write', callback);
            var data = {shape: 'diamond', color: 'purple', number: 2};
            store.add(new store.recordType(data));
        }); // add 2 purple diamonds

        asyncTest('load', function() {
            expect(2);
            store.load({callback: function(records, options, success){
                equals(records.length, 2, "Two records expected");
                equals(records[0].data.color, 'green', 'color of first record is green');
                start();
            }});
        }); // load
        
        asyncTest('removeAll', function() {
            expect(1);
            var callback = function(store, action, result, res, record) {
                equals(store.data.items.length, 0, 'store is empty');
                store.un('write', callback);
                start();
            };
            store.on('write', callback);
            store.removeAll();
        }); // removeAll
    
        asyncTest('load empty store', function() {
            expect(1);
            store.load({callback: function(records, options, success){
                equals(records.length, 0, "No records expected after removeAll");
                start();
            }});
        }); // load empty store
        
    })(); // module 1
    
    
    /* ***********************************************************************
     * Module 2: test a store with the remote sort enabled
     *
     */
    
    (function(){
        
        module('directstore: remote sort');
        
        var store = new Ext.data.DirectStore(
            Ext.apply({remoteSort: true}, baseStoreConfig));
            
        store.on('exception', function(misc) {
            ok(false, 'exception: ' + misc);
        });
        
        asyncTest('initial load of empty store', function() {
            expect(3);
            ok(!Ext.isDefined(baseStoreConfig.remoteSort), 'did not monkey with storeConfig');
            ok(store.remoteSort, 'remote sort is enabled');
            store.load({callback: function(records, options, success){
                equals(records.length, 0, "No records expected on initial load");
                start();
            }});
        }); // initial load
        
        asyncTest('add 3 green ovals', function() {
            expect(1);
            var callback = function(store, action, result, res, record) {
                equals(record.data.id, 0, 'id is 0');
                store.un('write', callback);
                start();
            };
            store.on('write', callback);
            var data = {shape: 'oval', color: 'green', number: 3};
            store.add(new store.recordType(data));
        }); // add 3 green ovals
        
        asyncTest('add 2 purple diamonds', function() {
            expect(1);
            var callback = function(store, action, result, res, record) {
                equals(record.data.id, 1, 'id is 1');
                store.un('write', callback);
                start();
            };
            store.on('write', callback);
            var data = {shape: 'diamond', color: 'purple', number: 2};
            store.add(new store.recordType(data));
        }); // add 2 purple diamonds
        
        asyncTest('load', function() {
            expect(2);
            store.load({callback: function(records, options, success){
                equals(records.length, 2, "Two records expected");
                equals(records[0].data.color, 'green', 'color is green');
                start();
            }});
        }); // load
        
        asyncTest('sort', function() {
            expect(2);
            var callback = function(store, records, options) {
                equals(records.length, 2, "Two records expected");
                equals(records[0].data.color, 'purple', 'color of first record is purple');
                store.un('load', callback);
                start();
            };
            store.on('load', callback);
            store.sort('color', 'DESC');
        }); // sort
        
        asyncTest('removeAll', function() {
            expect(1);
            var callback = function(store, action, result, res, record) {
                equals(store.data.items.length, 0, 'store is empty');
                store.un('write', callback);
                start();
            };
            store.on('write', callback);
            store.removeAll();
        }); // removeAll
        
        asyncTest('load empty store', function() {
            expect(1);
            store.load({callback: function(records, options, success){
                equals(records.length, 0, "No records expected after removeAll");
                start();
            }});
        }); // load empty store
        
    })(); // module 2
    
});
