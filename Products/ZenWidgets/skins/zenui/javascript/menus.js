var calcSubmenuPos = function(rel, sub) {
    // rel is the parent that triggered the submenu show
    var pPos  = getElementPosition(rel);
    var pDims = getElementDimensions(rel);
    var sDims = getElementDimensions(sub);
    var vDims = getViewportDimensions();

    // Check to see if the menu will appear outside the viewport
    // If so, make it fly out on the left
    totalX = pPos.x + pDims.w + sDims.w;
    if (totalX >= vDims.w) {
        return {x:-sDims.w+2, y:0}
    } else {
        return {x:sDims.w-10, y:10}
    }
}
var calcContextPos = function(menu) {
    var mPos = getElementPosition(menu);
    var mDim = getElementDimensions(menu);
    var vDim = getViewportDimensions();

    totalX = mPos.x + mDim.w;
    if (totalX >= vDim.w) {
        mPos.x -= mDim.w
    };
    return mPos;
}

var showSubMenu = function(rel, sub) {
    var relPos = calcSubmenuPos(rel, sub);
    setElementPosition(sub, relPos);
    setStyle(sub, {'visibility':'visible'});
}
var hideSubMenu = function(sub) {
    setStyle(sub, {'visibility':'hidden'});
}

var showContextMenu = function() {
    var menu = $('contextmenuitems');

}

var smto = Array();
var registerSubmenu = function(menu, submenu) {
    connect(menu, 'onmouseover', function() {
        clearTimeout(smto[submenu]);
        showSubMenu(menu, submenu); });
    connect(submenu, 'onmouseover', function() {
        clearTimeout(smto[submenu]);
        showSubMenu(menu, submenu); });
    connect(menu, 'onmouseout', function() {
        smto[submenu] = setTimeout('hideSubMenu("'+submenu+'")', 500); });
    connect(submenu, 'onmouseout', function() {
        smto[submenu] = setTimeout('hideSubMenu("'+submenu+'")', 500); });
}

console.log('Menu javascript loaded.');
