var calcSubmenuPos = function(rel, sub) {
    // rel is the parent that triggered the submenu show
    var pPos  = getElementPosition(rel);
    var pDims = getElementDimensions(rel);
    var sDims = getElementDimensions(sub);
    var vDims = getViewportDimensions();
    finalDims = {x:0, y:0}
    // Check to see if the menu will appear outside the viewport
    // If so, make it fly out on the left
    totalX = pPos.x + pDims.w + sDims.w;
    finalDims.x = totalX>=vDims.w?-sDims.w+2:sDims.w-10;
    // Check to see if the menu bottom is outside the viewport
    // If so, move it up so that it fits
    totalY = pPos.y + sDims.h;
    finalDims.y = totalY>=vDims.h?0-(totalY-vDims.h):0;
    return finalDims
}


var calcMenuPos = function(rel, menu) {
    var pPos = getElementPosition(rel);
    var pDims = getElementDimensions(rel);
    var vDims = getViewportDimensions();
    var mDims = getElementDimensions(menu);
    finalDims = $(menu).className=='devmovemenuitems'?{x:0, y:0}:{x:0, y:24};
    totalX = pPos.x + mDims.w;
    finalDims.x = totalX>=vDims.w?pDims.w-mDims.w:finalDims.x;
    finalDims.x = $(menu).className=='devmovemenuitems'?-mDims.w:finalDims.x;
    totalY = pPos.y + mDims.h;
    finalDims.y = totalY>=vDims.h?24:finalDims.y;
    return finalDims
}

var showSubMenu = function(rel, sub) {
    var relPos = calcSubmenuPos(rel, sub);
    setElementPosition(sub, relPos);
    setStyle(sub, {'visibility':'visible','z-index':'10001','opacity':'0.98'});
    hideOtherSubmenus(rel, sub);
}

var hideSubMenu = function(sub) {
    setStyle(sub, {'visibility':'hidden','z-index':'1'});
}

var hideMenu = function(menu) {
    setStyle(menu, {'visibility':'hidden','z-index':'1'});
}

var showMenu = function(rel, menu) {
    dropOtherMenuButtons(rel);
    var relPos = calcMenuPos(rel, menu);
    setElementPosition(menu, relPos);
    setStyle(menu, {'visibility':'visible','z-index':'10000','opacity':'0.98'});
}

var showContextMenu = function() {
    var menu = $('contextmenuitems');

}

var dropOtherMenuButtons = function(button) {
    mymenu = $(button).parentNode;
    others = getElementsByTagAndClassName('div','littlemenu');
    for (i=0;(btn=others[i]);++i) {
        if (btn!=mymenu) setStyle(btn, {'z-index':'9000'});
    }
    setStyle(mymenu, {'z-index':'10000'});
}

var hideOtherSubmenus = function(menu, submenu) {
    submenu = $(submenu);
    others = getElementsByTagAndClassName('div', 'submenu', menu.parentNode);
    for (i=0;(sub=others[i]);++i) {
        if (submenu!=sub) hideSubMenu(sub);
    }
}

var smto = Array();

var registerSubmenu = function(menu, submenu) {
    connect(menu, 'onmouseover', function() {
        clearTimeout(smto[menu]);
        clearTimeout(smto[submenu]);
        showSubMenu(menu, submenu); });
    connect(submenu, 'onmouseover', function() {
        clearTimeout(smto[menu]);
        clearTimeout(smto[submenu]);
        showSubMenu(menu, submenu); });
    connect(menu, 'onmouseout', function() {
        smto[submenu] = setTimeout('hideSubMenu("'+submenu+'")', 500); });
    connect(submenu, 'onmouseout', function() {
        smto[submenu] = setTimeout('hideSubMenu("'+submenu+'")', 500); });
}

var registerMenu = function(button, menu) {
    connect(button, 'onclick', function() {
        clearTimeout(smto[menu]);
        showMenu(button, menu);
        addElementClass(button, 'menuselected');
        connect(button, 'onmouseover', function() {
            clearTimeout(smto[menu]);
            showMenu(button, menu);
            addElementClass(button, 'menuselected');
        });
    });
    connect(menu, 'onmouseover', function() {
        clearTimeout(smto[menu]);
        showMenu(button, menu);
        addElementClass(button, 'menuselected');
        connect(button, 'onmouseover', function() {
            clearTimeout(smto[menu]);
            showMenu(button, menu);
            addElementClass(button, 'menuselected');
        });
    });
    connect(button, 'onmouseout', function() {
        smto[menu] = setTimeout('hideMenu("'+menu+'");disconnectAll("'+
            button+'", "onmouseover");', 500); });
    connect(menu, 'onmouseout', function() {
        smto[menu] = setTimeout('hideMenu("'+menu+'");disconnectAll("'+
            button+'", "onmouseover");', 500); });
}


console.log('Menu javascript loaded.');
