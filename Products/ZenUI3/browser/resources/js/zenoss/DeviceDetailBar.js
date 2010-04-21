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

Zenoss.DeviceNameItem = Ext.extend(Ext.Container, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            //layout: 'vbox',
            defaults: {
                xtype: 'tbtext'
            },
            items: [{
                cls: 'devdetail-devname',
                ref: 'devname'
            },{
                ref: 'devclass',
                cls: 'devdetail-devclass'
            },{
                ref: 'ipAddress',
                cls: 'devdetail-ipaddress'
            }]
        });
        Zenoss.DeviceNameItem.superclass.constructor.call(this, config);
    }
});
Ext.reg('devnameitem', Zenoss.DeviceNameItem);


Zenoss.DeviceDetailBar = Ext.extend(Zenoss.LargeToolbar, {
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            cls: 'largetoolbar devdetailbar',
            height: 55,
            directFn: Zenoss.remote.DeviceRouter.getInfo,
            defaultType: 'devdetailitem',
            items: [{
                ref: 'iconitem',
                cls: 'devdetail-icon'
            },{
                cls: 'evdetail-sep',
                style: 'margin-right:4px;'
            },{
                xtype: 'devnameitem',
                ref: 'deviditem'
            },'-',{
                ref: 'eventsitem',
                label: _t('Events')
            },'-',{
                ref: 'statusitem',
                label: _t('Device Status')
            },'-',{
                ref: 'prodstateitem',
                label: _t('Production State')
            }]  
        });
        Zenoss.DeviceDetailBar.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        this.directFn({uid:uid}, function(result){
            Zenoss.env.icon = this.iconitem;
            this.iconitem.getEl().setStyle({
                'background-image' : 'url(' + result.data.icon + ')'
            });
            this.deviditem.devname.setText(result.data.name);
            this.deviditem.ipAddress.setText(Zenoss.render.ipAddress(result.data.ipAddress));
            this.deviditem.devclass.setText(result.data.deviceClass.path);
            this.eventsitem.setText(Zenoss.render.events(result.data.events, 4));
            this.statusitem.setText(
                Zenoss.render.pingStatus(result.data.status));
            this.prodstateitem.setText(result.data.productionState);
        }, this);
    }
});

Ext.reg('devdetailbar', Zenoss.DeviceDetailBar);

})();
