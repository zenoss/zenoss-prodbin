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
    showElement('leftPaneToggle');
    makeInvisible(leftPane);
    makeInvisible($('paneToggle'));
    setStyle('paneToggle', {
        'background-image':'url(img/paneToggle_bg_collapsed.gif)',
    });
    setStyle('breadCrumbPane', { 'padding-left':'35px'});
    setStyle(rightPane, {'margin-left':'12px'});
    doHover();
}

function showLeftPane() {
    var leftPane = $('leftPane');
    var rightPane = $('rightPane');
    makeVisible(leftPane);
    makeVisible($('paneToggle'));
    hideElement('leftPaneToggle');
    setStyle('paneToggle', {
        'background-image':'url(img/paneToggle_bg.gif)',
    });
    setStyle('breadCrumbPane', { 'padding-left':'120px'});
    setStyle(rightPane, {'margin-left':'120px'});
    cancelHover();
}

function toggleLeftPane() {
    var leftPane = $('leftPane');
    if (!isVisible(leftPane)) { showLeftPane() }
    else { hideLeftPane() }
}

function doHiding() {
    hideElement($('leftPane'));
    hideElement($('paneToggle'));
}

function doShowing() {
    showElement($('leftPane'));
    showElement($('paneToggle'));
}

var t;
function doHover() {
    var leftPane = $('leftPane');
    var paneToggle = $('paneToggle');
    var leftPaneToggle = $('leftPaneToggle');
    var lpPopup = leftPane;
    setStyle(lpPopup, {
        'position':'absolute',
//        'background-color':'white',
//        'padding':'2px',
//        'padding-top':'2px',
        'z-index':'3000'
    });
    connect('leftPaneToggle', 'onclick', function(){
        clearTimeout(t);
        doShowing();
    });
    connect(leftPane, 'onmouseover', function(){
        clearTimeout(t);
        doShowing();
    });
    connect($('paneToggle'), 'onmouseover', function(){
        clearTimeout(t);
        doShowing();
    });
    connect(paneToggle,'onmouseout',function(){
        t=setTimeout('doHiding()',500);
    });
    connect(leftPane, 'onmouseout', function(){
        t=setTimeout('doHiding()',500);
    });
    connect(paneToggle, 'onclick', function(){
        clearTimeout(t);
        toggleLeftPane();
    });
    setCookie('Zenoss_Collapsed_Menu', 'true',30,'/','','');
}

function cancelHover() {
    var leftPane = $('leftPane');
    var paneToggle = $('paneToggle');
    disconnectAll(paneToggle);
    disconnectAll(leftPane);
    deleteCookie('Zenoss_Collapsed_Menu','/','');
    updateNodeAttributes(leftPane, {
        'style':'display:block'
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
