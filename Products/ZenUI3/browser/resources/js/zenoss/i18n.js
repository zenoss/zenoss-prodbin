(function(){

Ext.ns('Zenoss.i18n');

// Provide a default; this gets filled in later when appropriate.
Zenoss.i18n._data = {};

Zenoss.i18n.translate = function(s, d) {
    t = Zenoss.i18n._data[s];
    return t ? t : (d ? d: s);
}

// Shortcut
window._t = Zenoss.i18n.translate

})();
