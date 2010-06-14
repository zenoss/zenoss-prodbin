/*
 * Tooltips.js
 */
(function(){ // Local scope
/*
 * Zenoss.registerTooltip
 *
 * Make QuickTips also accept a target component or component ID to attach a
 * tooltip to. It will attempt to discover the correct Ext.Element to which it
 * should attach the tip.
 *
 * Accepts the same config options as the Ext.ToolTip constructor.
 *
 */

Zenoss.TIPS = {};

/*
* Zenoss.ToolTip
* Causes tooltips to remain visible if the mouse is over the tip itself,
* instead of hiding as soon as the mouse has left the target.
*/
Zenoss.ToolTip = Ext.extend(Ext.ToolTip, {
   constructor: function(config) {
       Zenoss.ToolTip.superclass.constructor.call(this, config);
       this.on('render', this.attachHoverEvents, this);
   },
   attachHoverEvents: function() {
       var el = this.getEl();
       el.on('mouseenter', this.onMouseEnter, this);
       el.on('mouseleave', this.onTargetOut, this);
   },
   onMouseEnter: function(e) {
       this.clearTimer('hide');
   }
});

Zenoss.registerTooltip = function(config) {
    var t, target = config.target,
        initialConfig = Ext.apply({}, config),
        cmp = Ext.getCmp(target);
    if (typeof(cmp)!="undefined") {
        cmp.on('destroy', function(){
            Zenoss.TIPS[target] = initialConfig;
        });
        if (cmp.btnEl) {
            config.target = cmp.btnEl;
        }
    } else {
        Ext.ComponentMgr.onAvailable(target, function(t){
            t.tooltip = config;
        });
    }
    if ((t=Ext.get(target))) {
        var tip = new Zenoss.ToolTip(config);
        Zenoss.TIPS[target] = tip;
    } else {
        Zenoss.TIPS[target] = initialConfig;
    }
}; // Zenoss.registerTooltip

/*
 * Zenoss.registerTooltipFor
 * 
 * Looks up any tooltips for a component id and registers them. Used for items
 * that don't exist when Zenoss.registerTooltip was called.
 *
 * If a tooltip is already registered, don't reregister it.
 *
 */
Zenoss.registerTooltipFor = function(target) {
    var t;
    if (Ext.isDefined(t = Zenoss.TIPS[target])) {
        if (!(t instanceof Ext.ToolTip)) {
            Zenoss.registerTooltip(t);
        }
    }
}; // Zenoss.registerTooltipFor


})(); // End local scope
