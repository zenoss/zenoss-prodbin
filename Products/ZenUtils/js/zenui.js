/* Panel Effects */

function toggleVisible(elem) {
    toggleElementClass("invisible", elem);
}

function makeVisible(elem) {
    removeElementClass(elem, "invisible");
}

function makeInvisible(elem) {
    addElementClass(elem, "invisible");
}

function isVisible(elem) {
    return !hasElementClass(elem, "invisible");
}

function getCookie(name) {
    var s = document.cookie.indexOf(name + "=");
    if ((!s) && name!=document.cookie.substring(0,name.length)) {
        return null;
    }
    if (s < 0) {
        return null;
    }
    var e = document.cookie.indexOf(';', s+name.length+1);
    if (e<0) e = document.cookie.length;
    if (e==s) {
        return '';
    }
    return unescape(document.cookie.substring(s+name.length+1, e));
}

function setCookie( name, value, expires, path, domain, secure ) {
    var today = new Date();
    today.setTime( today.getTime() );
    if ( expires ) {
        expires = expires * 1000 * 60 * 60 * 24;
    }
    var expires_date = new Date( today.getTime() + (expires) );
    document.cookie = name + "=" +escape( value ) +
        ( ( expires ) ? ";expires=" + expires_date.toGMTString() : "" ) +
        ( ( path ) ? ";path=" + path : "" ) +
        ( ( domain ) ? ";domain=" + domain : "" ) +
        ( ( secure ) ? ";secure" : "" );
}

function deleteCookie(name,path,domain) {
     if (getCookie(name)) {
         document.cookie =
         name + '=' +
         ( (path) ? ';path=' + path : '') +
         ( (domain) ? ';domain=' + domain : '') +
         ';expires=Thu, 01-Jan-1970 00:00:01 GMT';
     }
}

function hideLeftPane() {
    var leftPane = $('leftPane');
    var rightPane = $('rightPane');
    makeInvisible(leftPane);
    setStyle(rightPane, {'margin-left':'12px'});
    doHover();
}

function showLeftPane() {
    var leftPane = $('leftPane');
    var rightPane = $('rightPane');
    makeVisible(leftPane);
    setStyle(rightPane, {'margin-left':'108px'});
    cancelHover();
}

function toggleLeftPane() {
    var leftPane = $('leftPane');
    if (!isVisible(leftPane)) { showLeftPane() }
    else { hideLeftPane() }
}

function doHover() {
    var leftPane = $('leftPane');
    var paneToggle = $('paneToggle');
    var lpPopup = leftPane;
    var elemPos = getElementPosition(paneToggle);
    elemPos.x += 5;
    elemPos.y += 5;
    setElementPosition(lpPopup, elemPos);
    setStyle(lpPopup, {
        'position':'absolute',
        'background-color':'white',
        'padding':'2px',
        'padding-top':'2px',
        'border':'1px solid darkgrey'
    });
    connect(paneToggle, 'onmouseover', function(){showElement(lpPopup)});
    connect(leftPane, 'onmouseover', function(){showElement(lpPopup)});
    connect(paneToggle, 'onmouseout', function(){hideElement(lpPopup)});
    connect(leftPane, 'onmouseout', function(){hideElement(lpPopup)});
    setCookie('Zenoss_Collapsed_Menu', 'true',30,'/','','');
}

function cancelHover() {
    var leftPane = $('leftPane');
    var paneToggle = $('paneToggle');
    disconnectAll(paneToggle);
    disconnectAll(leftPane);
    deleteCookie('Zenoss_Collapsed_Menu','/','');
    setStyle(leftPane, {
        'background-color':'transparent',
        'padding':'25px 0 0 0',
        'margin':'5px 5px 10px 0',
        'top':'42px',
        'left':'4px',
        'border':'1px solid transparent'
    });
}

function checkForCollapsed() {
    var x = getCookie('Zenoss_Collapsed_Menu');
    log(x);
    if (!x){
        noop();
        //cancelHover();
    } else {
        hideLeftPane();
    }
}

addLoadEvent(checkForCollapsed);
