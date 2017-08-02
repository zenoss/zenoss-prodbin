/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


/* package level */
(function() {
Ext.define("Zenoss.form.DataPointItemSelector", {
    alias:['widget.datapointitemselector'],
    extend:"Ext.ux.form.ItemSelector",
    listeners: {
        // show datapoint name and its RPN according to datapoints that
        // were selected in selector form
        change: function(obj, event) {
            rpnTextObj = Ext.ComponentQuery.query('[name=rpnused]')[0];
            if (rpnTextObj) {
                rpnTextObj.setValue('');
                Ext.each(obj.getValue(), function(dpname, index){
                    rpnTextObj.setValue(rpnTextObj.value + dpname + ": " + rpnTextObj.record.allDataPoints[dpname] + "; ");
                });
            }
        }
    },
    constructor: function(config) {
        var record = config.record;

        this.value = config.value;

        Ext.applyIf(config, {
            name: 'dataPoints',
            fieldLabel: _t('Data Points'),
            id: 'thresholdItemSelector',
            imagePath: "/++resource++zenui/img/xtheme-zenoss/icon",
            drawUpIcon: false,
            drawDownIcon: false,
            drawTopIcon: false,
            drawBotIcon: false,
            store: Object.keys(record.allDataPoints)
        });
        this.callParent(arguments);
    },
    /**
     * In ExtJs 4.1 The ItemsSelect getValue doesn't work at all.
     *
     * To work around this we can just grab everything in the toField store.
     *
     */
    getValue: function(){
        var store = this.toField.getStore();
        return Ext.pluck(Ext.pluck(store.data.items, 'data'), 'field1');
    }
});

}());
