(function(){

Zenoss.DeviceDetailItem = Ext.extend(Ext.Container, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            hideParent: true,
            cls: 'devdetailitem',
            items: [{
                cls: 'devdetail-textitem ' + (config.textCls||''),
                ref: 'textitem',
                xtype: 'tbtext',
                text: config.text || ''
            },{
                cls: 'devdetail-labelitem ' + (config.labelCls||''),
                ref: 'labelitem',
                xtype: 'tbtext',
                text: config.label || ''
            }]
        });
        Zenoss.DeviceDetailItem.superclass.constructor.call(this, config);
    },
    setText: function(t) {
        this.textitem.setText(t);
    },
    setLabel: function(t) {
        this.labelitem.setText(t);
    }
});

Ext.reg('devdetailitem', Zenoss.DeviceDetailItem);

Zenoss.DeviceDetailBar = Ext.extend(Zenoss.LargeToolbar, {
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            cls: 'largetoolbar devdetailbar',
            height: 55,
            directFn: Zenoss.remote.DeviceRouter.getInfo,
            defaultType: 'devdetailitem',
            items: [{
                ref: 'deviditem',
                textCls: 'devdetail-devname',
                labelCls: 'devdetail-ipaddress'
            },'-',{
                ref: 'eventsitem',
                label: _t('Events')
            },'-',{
                ref: 'statusitem',
                label: _t('Device Status')
            },'-',{
                ref: 'availabilityitem',
                label: _t('Availability')
            },'-',{
                ref: 'prodstateitem',
                label: _t('Production State')
            },'-',{
                ref: 'collectoritem',
                label: _t('Collector')
            }]  
        });
        Zenoss.DeviceDetailBar.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        this.directFn({uid:uid}, function(result){
            this.deviditem.setText(result.data.name);
            this.deviditem.setLabel(
                Zenoss.render.ipAddress(result.data.ipAddress)
            );
            this.eventsitem.setText(Zenoss.render.events(result.data.events));
            this.statusitem.setText(
                Zenoss.render.pingStatus(result.data.status)
            );
            this.availabilityitem.setText(
                Zenoss.render.availability(result.data.availability)
            );
            this.prodstateitem.setText(result.data.productionState);
            this.collectoritem.setText(result.data.collector);
        }, this);
    }
});

Ext.reg('devdetailbar', Zenoss.DeviceDetailBar);

})();
