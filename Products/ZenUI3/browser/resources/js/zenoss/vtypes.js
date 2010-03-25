(function(){
    Ext.ns('Zenoss.VTypes');
    
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
        betweenzeroandoneText: _t('Must be between 0 and 1')
    };
     
    Ext.apply(Ext.form.VTypes, vtypes);
}());