var calcSubmenuPos = function(rel, sub) {
    // rel is the parent that triggered the submenu show
    var pPos  = getElementPosition(rel);
    var pDims = getElementDimensions(rel);
    var sDims = getElementDimensions(sub);
    var vDims = getViewportDimensions();
    var vPos = getViewportPosition();
    finalDims = {x:0, y:0}
    // Check to see if the menu will appear outside the viewport
    // If so, make it fly out on the left
    totalX = pPos.x + pDims.w + sDims.w;
    finalDims.x = totalX>=vDims.w+vPos.x?-sDims.w+2:sDims.w-10;
    // Check to see if the menu bottom is outside the viewport
    // If so, move it up so that it fits
    totalY = pPos.y + sDims.h;
    finalDims.y = totalY>=vDims.h+vPos.y?0-(totalY-vDims.h)+vPos.y:0;
    return finalDims
}


var calcMenuPos = function(rel, menu) {
    var pPos = getElementPosition(rel);
    var pDims = getElementDimensions(rel);
    var vDims = getViewportDimensions();
    var mDims = getElementDimensions(menu);
    var vPos = getViewportPosition();
    finalDims = $(menu).className=='devmovemenuitems'?{x:0, y:0}:{x:0, y:24};
    totalX = pPos.x + mDims.w;
    finalDims.x = totalX>=vDims.w+vPos.x?pDims.w-mDims.w:3+finalDims.x;
    finalDims.x = $(menu).className=='devmovemenuitems'?4-pDims.w:finalDims.x;
    finalDims.x -= 1;
    totalY = pPos.y + pDims.h + mDims.h;
    var topmenu = getElementsByTagAndClassName('div', 'menu_top', menu)[0];
    if (totalY>=vDims.h+vPos.y) {
        finalDims.y = 0-(totalY-vDims.h)+vPos.y;
        setStyle(topmenu, {'background-image':'url(img/menu_top_rounded.gif)'});
    } else {
        setStyle(topmenu, {'background-image':'url(img/menu_top.gif)'});
    }
    return finalDims
}

var showSubMenu = function(rel, sub) {
    var relPos = calcSubmenuPos(rel, sub);
    setElementPosition(sub, relPos);
    setStyle(sub, {'visibility':'visible','z-index':'10001'});
    hideOtherSubmenus(rel, sub);
}

var hideSubMenu = function(sub) {
    setStyle(sub, {'visibility':'hidden','z-index':'1'});
}

var hideMenu = function(menu) {
    setStyle(menu, {'visibility':'hidden','z-index':'1'});
    try {
    setStyle(getFirstParentByTagAndClassName(menu, 'div',
        'tabletitlecontainer'), {'z-index':'1'});
    } catch(e){noop()}
    if (navigator.userAgent.match('Mac')) {
        try {setStyle(eventZenGrid.scrollbar, {'overflow':'auto'})}
        catch(e) {noop()};
    }
}

var showMenu = function(rel, menu) {
    dropOtherMenuButtons(rel);
    var relPos = calcMenuPos(rel, menu);
    setElementPosition(menu, relPos);
    setStyle(menu, {'visibility':'visible','z-index':'10000',
                    'zoom':1});
    if (navigator.userAgent.match('Mac')) {
        try {setStyle(eventZenGrid.scrollbar, {'overflow':'hidden'})}
        catch(e) {noop()};
    }
}

var showContextMenu = function() {
    var menu = $('contextmenuitems');

}

var dropOtherMenuButtons = function(button) {
    var lowerButton = function(btn) { setStyle(btn, {'z-index':'1'})};
    try {
        mymenu = getFirstParentByTagAndClassName($(button).parentNode, 'div',
        'tabletitlecontainer');
    } catch(e) {
        mymenu = null;
    }
    others = $$("div.tabletitlecontainer");
    map(lowerButton, others);
    if (mymenu) setStyle(mymenu, {'z-index':'10000'});
}

var hideOtherSubmenus = function(menu, submenu) {
    var smartHideSub = function(sub){if ($(submenu)!=sub) hideSubMenu(sub)}
    map(smartHideSub, $$('div.submenu'));
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
    connect(submenu, 'onclick', function() {
        hideSubMenu(submenu);
    });
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
    connect(menu, 'onclick', function() {
        hideMenu(menu);
        disconnectAll(button, 'onmouseover');
    });
    connect(button, 'onmouseout', function() {
        smto[menu] = setTimeout('hideMenu("'+menu+'");disconnectAll("'+
            button+'", "onmouseover");', 500); });
    connect(menu, 'onmouseout', function() {
        smto[menu] = setTimeout('hideMenu("'+menu+'");disconnectAll("'+
            button+'", "onmouseover");', 500); });
}


log('Menu javascript loaded.');
