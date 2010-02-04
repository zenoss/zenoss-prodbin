/*
 * Utility for keeping track of navigation among subcomponents on a page and
 * restoring that state on page load. 
 */
(function(){

var H = Ext.History;
H.DELIMITER = ':';

H.selectByToken = function(token) {
    if(token) {
        var parts = token.split(H.DELIMITER),
            mgr = Ext.getCmp(parts[0]),
            remainder = parts.slice(1).join(H.DELIMITER);
        if (mgr) {
            mgr.selectByToken(remainder);
        }
    }
};

H.on('change', H.selectByToken);

})();
