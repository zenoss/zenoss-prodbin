(function(){

Ext.define("Zenoss.DeviceDetailItem", {
    alias:['widget.devdetailitem'],
    extend:"Ext.Container",
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



Ext.define("Zenoss.DeviceNameItem", {
    alias:['widget.devnameitem'],
    extend:"Ext.Container",
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
                style: 'margin-top:0;',
                cls: 'devdetail-ipaddress'
            }]
        });
        Zenoss.DeviceNameItem.superclass.constructor.call(this, config);
    }
});



Ext.define("Zenoss.DeviceDetailBar", {
    alias:['widget.devdetailbar'],
    extend:"Zenoss.LargeToolbar",
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
                xtype: "eventrainbow",
                width:202,
                ref: 'eventsitem',
                style: 'padding-top:6px;',
                id: 'detailrainbow',
                label: _t('Events'),
                listeners: {
                    'render': function(me) {
                        me.getEl().on('click', function(){
                            Ext.History.add('#deviceDetailNav:device_events');
                        });
                    }
                },
                count: 4
            },'-',{
                ref: 'statusitem',
                width:98,
                label: _t('Device Status'),
                id: 'statusitem'
            },'-',{
                ref: 'prodstateitem',
                width:120,
                label: _t('Production State'),
                id: 'prodstateitem'
            },'-',{
                ref: 'priorityitem',
                width:100,
                label: _t('Priority'),
                id: 'priorityitem'
            }]
        });
        this.contextKeys = [
            'ipAddressString',
            'deviceClass',
            'name',
            'icon',
            'events',
            'status',
            'productionState',
            'priority'
        ];
        Zenoss.DeviceDetailBar.superclass.constructor.call(this, config);
    },
    contextCallbacks: [],
    addDeviceDetailBarItem: function(item, fn, added_keys) {
      this.add('-');
      this.add(item);
      this.on('contextchange', fn, this);
      for (var i = 0; i < added_keys.length; i++) {
        this.contextKeys.push(added_keys[i]);
      }
    },
    refresh: function() {
        this.setContext(this.contextUid);
    },
    setContext: function(uid) {
        this.contextUid = uid;
        this.directFn({uid:uid, keys:this.contextKeys}, function(result){
            var ZR = Zenoss.render,
                data = result.data;
            Zenoss.env.icon = this.iconitem;
            this.iconitem.getEl().setStyle({
                'background-image' : 'url(' + data.icon + ')'
            });
            this.deviditem.devname.setText(data.name);
            var ipAddress = data.ipAddressString;
            this.deviditem.ipAddress.setHeight(Ext.isEmpty(ipAddress) ? 0 : 'auto');
            this.deviditem.ipAddress.setText(ipAddress);
            this.deviditem.devclass.setText(ZR.DeviceClass(data.deviceClass.uid));
            this.eventsitem.updateRainbow(data.events);
            this.statusitem.setText(
                ZR.pingStatusLarge(data.status));
            this.prodstateitem.setText(Zenoss.env.PRODUCTION_STATES_MAP[data.productionState]);
            this.priorityitem.setText(Zenoss.env.PRIORITIES_MAP[data.priority]);
            this.fireEvent('contextchange', this, data);
        }, this);
    }
});



})();
