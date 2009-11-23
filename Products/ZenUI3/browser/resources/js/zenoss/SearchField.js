Ext.ns('Zenoss');

/**
 * @class Zenoss.SearchField
 * @extends Ext.form.TextField
 * @constructor
 */
Zenoss.SearchField = Ext.extend(Ext.form.TextField, {
    constructor: function(config){
        if (!('selectOnFocus' in config))
            config.selectOnFocus = true;
        Zenoss.SearchField.superclass.constructor.apply(this, arguments);
    },
    getClass: function(){
        return this.black ? 'searchfield-black' : 'searchfield';
    },
    onRender: function() {
        Zenoss.SearchField.superclass.onRender.apply(this, arguments);
        this.wrap = this.el.boxWrap(this.getClass());
        if (this.bodyStyle) {
            this.wrap.setStyle(this.bodyStyle);
        }
        this.resizeEl = this.positionEl = this.wrap;
        this.syncSize();
    },
    syncSize: function(){
        this.el.setBox(this.el.parent().getBox());
    }

}); // Ext.extend

Ext.reg('searchfield', Zenoss.SearchField);
