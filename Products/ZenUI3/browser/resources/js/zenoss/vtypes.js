(function(){
    Ext.ns('Zenoss.VTypes');

    var ip_regex = new RegExp("(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)");
    
    /**
     * These are the custom validators defined for
     * our zenoss forms. The xtype/vtype custom is to have the
     * name of the vtype all lower case with no word separator.
     *
     **/
    var vtypes = {

        /**
         * The number must be greater than zero. Designed for us in NumberFields
         **/
        positive: function(val, field) {
            return (val > 0);
        },
        positiveText: _t('Must be greater than 0'),

        /**
         * Between 0 and 1 (for float types)
         **/
        betweenzeroandone: function(val, field) {
            return (val >= 0 && val <=1);
        },
        betweenzeroandoneText: _t('Must be between 0 and 1'),
        ipaddress: function(val, field) {
            return ip_regex.test(val);
        },
        ipaddressText: _t('Invalid IP address')
    };
     
    Ext.apply(Ext.form.VTypes, vtypes);
}());
