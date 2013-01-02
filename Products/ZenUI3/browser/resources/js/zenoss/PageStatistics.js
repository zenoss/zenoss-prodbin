(function(){

    /**
     * Classes for determining when the page is completely loaded. Since this
     * is set per page encapsulate the logic here.
     *
     **/
    Ext.define("Zenoss.stats.ResultsWindow", {
        extend: "Zenoss.dialog.BaseDialog",
        constructor: function(config) {
            var finalTime = config.finalTime,
                loadingTime = config.loadingTime;

            Ext.applyIf(config, {
                title: _t('Page Load Time'),
                defaults: {
                    xtype: 'displayfield'
                },
                items: [{
                    value: Ext.String.format(_t("{0} seconds until the page is ready to use."), loadingTime)
                }, {
                    value: Ext.String.format(_t("{0} seconds in layout and rendering on the client."), (finalTime - Zenoss._pageStartTime).toFixed(2))
                }, {
                    value: Ext.String.format(_t("{0} seconds since ExtJs start time."), (finalTime - (Ext._startTime/1000)).toFixed(2))
                }]

            });
            this.callParent([config]);
        }


    });

    Ext.define("Zenoss.stats.Infrastructure", {
        constructor: function() {
            this.addHooks();
        },
        addHooks: function() {
            // the Infrastructure page is loaded when the both the trees
            // and grid stores are loaded and rendered. Since
            // we don't really load the store until after the Devices tree is rendered
            // we can assume the page is fully loaded when the Device grid has finished loading
            // its store.
            Ext.getCmp('device_grid').getStore().on('load', this.checkReady, this, {single:true});
        },
        getTiming: function() {
            var perf = window.performance || {};
            var fn = perf.now || perf.mozNow || perf.webkitNow || perf.msNow || perf.oNow;
            return fn ? fn.bind(perf) : null;
        },
        checkReady: function() {

            // convert from milliseconds to seconds
            var finalTime = new Date().getTime() / 1000.0,
                loadingTime = this.getTiming()();
            // perf data is unavailable, display nothing
            if (!loadingTime) {
                return;
            }

            loadingTime = (loadingTime / 1000.00).toFixed(2);
            Ext.getCmp('footer_bar').add(['-', {
                xtype: 'button',
                text: Ext.String.format(_t("{0} seconds"), loadingTime),
                handler: function(){
                    Ext.create('Zenoss.stats.ResultsWindow', {finalTime: finalTime, loadingTime: loadingTime}).show();
                }
            }]);
        }


    });

    Ext.define("Zenoss.stats.Events", {
        extend: "Zenoss.stats.Infrastructure",
        addHooks: function() {
            Ext.getCmp('events_grid').getStore().on('load', this.checkReady, this, {single:true});
        }

    });

    Ext.define("Zenoss.stats.DeviceDetail", {
        extend: "Zenoss.stats.Infrastructure",
        addHooks: function() {
            var detailnav = Ext.getCmp('deviceDetailNav');
            detailnav.on('componenttreeloaded', this.checkReady, this, {single:true});
        }

    });

}());