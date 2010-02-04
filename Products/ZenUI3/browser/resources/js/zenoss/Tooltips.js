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
Zenoss.registerTooltip = function(config) {
    var cmp = Ext.getCmp(config.target);
    if (typeof(cmp)!="undefined") {
        if (cmp.btnEl) {
            config.target = cmp.btnEl;
        }
    }
    new Ext.ToolTip(config);

}; // Zenoss.registerTooltip

})(); // End local scope
