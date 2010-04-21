(function(){

Zenoss.DeviceOverviewPanel = Ext.extend(Ext.Panel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
        });
        Zenoss.DeviceOverviewPanel.superclass.constructor.call(this, config);
    }
});

Ext.reg('deviceoverview', Zenoss.DeviceOverviewPanel);

})();
