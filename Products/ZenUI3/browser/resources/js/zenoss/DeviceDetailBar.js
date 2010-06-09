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
                ref: 'deviditem',
                style: 'margin-right: 8px;'
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
    contextCallbacks: [],
    addDeviceDetailBarItem: function(item, fn) {
      this.items.push('-')
      this.items.push(item)
      this.on('contextchange',fn,this)
    },
    refresh: function() {
        this.setContext(this.contextUid);
    },
    setContext: function(uid) {
        this.contextUid = uid;
        this.directFn({uid:uid}, function(result){
            var ZR = Zenoss.render,
                data = result.data;
            Zenoss.env.icon = this.iconitem;
            this.iconitem.getEl().setStyle({
                'background-image' : 'url(' + data.icon + ')'
            });
            this.deviditem.devname.setText(data.name);
            var ipAddress = ZR.ipAddress(data.ipAddress);
            this.deviditem.ipAddress.setHeight(Ext.isEmpty(ipAddress) ? 0 : 'auto');
            this.deviditem.ipAddress.setText(ipAddress);
            this.deviditem.devclass.setText(ZR.DeviceClass(data.deviceClass.uid));
            this.eventsitem.setText(ZR.events(data.events, 4));
            this.statusitem.setText(
                ZR.pingStatusLarge(data.status));
            this.prodstateitem.setText(data.productionState);
            this.fireEvent('contextchange', this, data)
        }, this);
    }
});

Ext.reg('devdetailbar', Zenoss.DeviceDetailBar);

})();
