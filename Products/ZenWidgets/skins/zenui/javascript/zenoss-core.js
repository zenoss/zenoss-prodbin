// Set up the Javascript loader
loader = new YAHOO.util.YUILoader();
loader.base = '/zport/dmd/yui/';

// Register zenoss scripts
loader.addModule({
    name: "datatablesamskin",
    type: "css",
    fullpath: "/zport/dmd/yui/datatable/assets/skins/sam/datatable.css"
});
loader.addModule({
    name: "autocompleteskin",
    type: "css",
    fullpath: "/zport/dmd/yui/autocomplete/assets/skins/sam/autocomplete.css"
});
loader.addModule({
    name: "portletsource",
    type: "js",
    fullpath: "/zport/ZenPortletManager/get_source",
    requires: ["portlet","dragdrop", "event", "dom", "animation", 
               "datasource", "datatable", "datatablesamskin",
               "container", "button","zenautocomplete"]
});
loader.addModule({
    name: "zenautocomplete",
    type: "js",
    fullpath: "/zport/dmd/javascript/zenautocomplete.js",
    requires: ["autocomplete", "animation", "autocompleteskin"]
});

//Declare the Zenoss namespace
YAHOO.namespace("zenoss");

// Put the loader somewhere accessible
YAHOO.namespace("zenoss.loader");
YAHOO.zenoss.loader = loader;

// Define a helpful "class" function (thanks, Prototype)

var Class={
    create:function(){
        return function(){
            bindMethods(this);
            this.__init__.apply(this,arguments);
        } 
    }
}

YAHOO.zenoss.Class = Class;


function bindMethodsTo(src, scope) {
    for (var property in src) {
        if (typeof src[property]=='function') {
            src[property] = method(scope, src[property]);
        }
    }
}

// Subclassing! (thanks, me)

var Subclass={
    create: function(klass){
        return function() {
            this.superclass = {};
            for (var property in klass.prototype) {
                if (!(property in this))
                    this[property] = klass.prototype[property];
                    this.superclass[property] = klass.prototype[property];
            }
            bindMethods(this);
            bindMethodsTo(this.superclass, this);
            this.__init__.apply(this, arguments);
        }
    }
}
YAHOO.zenoss.Subclass = Subclass;


function purge(d) {
    var a = d.attributes, i, l, n;
    if (a) {
        l = a.length;
        for (i = 0; i < l; i += 1) {
            n = a[i].name;
            if (typeof d[n] === 'function') {
                d[n] = null;
            }
        }
    }
    a = d.childNodes;
    if (a) {
        l = a.length;
        for (i = 0; i < l; i += 1) {
            purge(d.childNodes[i]);
        }
    }
}
YAHOO.zenoss.purge = purge;

/************************************
 *   Less universally useful stuff
 *   (formerly separate scripts)
 ***********************************/
 
function toggleElement(elementid) {
    var element = $(elementid);
    if (element.visible == 0) {
        element.style.display = "none";
        element.visible = 1;
    } else {
        element.style.display = "";
        element.visible = 0;
    }
}


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
    //showElement('leftPaneToggle');
    makeInvisible(leftPane);
    makeInvisible($('paneToggle'));
    setStyle('paneToggle', {
        'background-image':'url(img/paneToggle_bg_collapsed.gif)',
        'border-right':'1px solid black'
    });
    if ($('breadCrumbPane')) {
    setStyle('breadCrumbPane', { 'padding-left':'35px'});}
    setStyle('rightPane', {'margin-left':'12px'});
    setStyle('leftPaneToggle', {
    'background':'transparent url(img/leftpanetoggle_bg.gif) top left repeat-x',
    'height':'30px',
    'width':'30px'
    });
    disconnectAll('leftPaneToggle');
    connect('leftPaneToggle', 'onclick', function(){
        clearTimeout(t);
        doShowing();
    });
    doHover();
}

function showLeftPane() {
    var leftPane = $('leftPane');
    var rightPane = $('rightPane');
    makeVisible(leftPane);
    makeVisible($('paneToggle'));
    //hideElement('leftPaneToggle');
    setStyle('paneToggle', {
        'background-image':'url(img/paneToggle_bg.gif)',
        'border-right':'1px solid black'
    });
    if ($('breadCrumbPane')) {
    setStyle('breadCrumbPane', { 'padding-left':'120px'});}
    setStyle(rightPane, {'margin-left':'120px'});
    setStyle('leftPaneToggle', {
    'background':'#5a6f8f url(img/leftpanetoggle_bg_expanded.gif) ' +
        'top left repeat-x',
    'height':'30px',
    'width':'115px'
    });
    disconnectAll('leftPaneToggle');
    connect('leftPaneToggle','onclick',toggleLeftPane);
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
    setStyle(paneToggle, {
        'z-index':'10000'
    });
    setStyle(lpPopup, {
        'position':'absolute',
//        'background-color':'white',
//        'padding':'2px',
//        'padding-top':'2px',
        'z-index':'10000'
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
    connect('leftPaneToggle', 'onmouseout', function(){
        t=setTimeout('doHiding()',500);
    });
    connect(paneToggle, 'onclick', function(){
        clearTimeout(t);
        toggleLeftPane();
    });
    connect('leftPaneToggle','onmouseover', function() {
        setStyle('leftPaneToggle', {
            'background':'transparent ' +
            'url("img/leftpanetoggle_bg_depressed.gif") top left repeat-x'
            })
    });
    connect('leftPaneToggle','onmouseout', function() {
        setStyle('leftPaneToggle', {
            'background':'transparent ' +
            'url("img/leftpanetoggle_bg.gif") top left repeat-x'
            })
    });
    connect('leftPaneToggle', 'onclick', function(){
        clearTimeout(t);
        doShowing();
    });
    setCookie('Zenoss_Collapsed_Menu', 'true',30,'/','','');
}

function cancelHover() {
    var leftPane = $('leftPane');
    var paneToggle = $('paneToggle');
    if (leftPane && paneToggle) {
        setStyle(paneToggle, {'z-index':'1'});
        setStyle(leftPane, {'z-index':'1'});
    disconnectAll(paneToggle);
    disconnectAll(leftPane);
    disconnectAll('leftPaneToggle');
    connect('leftPaneToggle', 'onclick', toggleLeftPane);
    connect('leftPaneToggle','onmouseover', function() {
        setStyle('leftPaneToggle', {
            'background':'transparent ' +
            'url("img/leftpanetoggle_bg_expanded_depressed.gif") '+
            'top left repeat-x'
            })
    });
    connect('leftPaneToggle','onmouseout', function() {
        setStyle('leftPaneToggle', {
            'background':'transparent ' +
            'url("img/leftpanetoggle_bg_expanded.gif") top left repeat-x'
            })
    });
    deleteCookie('Zenoss_Collapsed_Menu','/','');
    updateNodeAttributes(leftPane, {
        'style':'display:block'
    });}
}

function checkForCollapsed() {
    var x = getCookie('Zenoss_Collapsed_Menu');
    if ($('leftPaneToggle')){
    if (!x){
    disconnectAll('leftPaneToggle');
    connect('leftPaneToggle','onclick',toggleLeftPane);
    connect('leftPaneToggle','onmouseover', function() {
        setStyle('leftPaneToggle', {
            'background':'transparent ' +
            'url("img/leftpanetoggle_bg_expanded_depressed.gif") top left repeat-x'
            })
    });
    connect('leftPaneToggle','onmouseout', function() {
        setStyle('leftPaneToggle', {
            'background':'transparent ' +
            'url("img/leftpanetoggle_bg_expanded.gif") top left repeat-x'
            })
    });
    } else {
        hideLeftPane();
    }
    }
}

function getChildCheckboxes(element) {
    return filter(
        function(x){return x.type=='checkbox'},
        element.getElementsByTagName('input')
    )
}

var tablesOnPage=0;
function insertSelBar(table) {
    var getselall = function() {
        return function() {selectAllCheckboxes(table)}
    }
    var getselnone = function() {
        return function() {selectNoneCheckboxes(table)}
    }
    var all = LI(null, 'All');
    var nun = LI(null, 'None');
    var selbar = DIV({'class':'zentable_selectionbar'}, 
        [ 'Select:  ', UL(null, [all, nun ]) ]);
    insertSiblingNodesBefore(table, selbar);
    connect(all, 'onclick', getselall());
    connect(nun, 'onclick', getselnone());
}

function selectAllCheckboxes(table) {
    var cbs = getChildCheckboxes(table);
    map(function(x){x.checked=true},cbs);
}

function selectNoneCheckboxes(table) {
    var cbs = getChildCheckboxes(table);
    map(function(x){x.checked=null},cbs);
}

function addSelectionBar() {
    var tables = getElementsByTagAndClassName('table', 'innerzentable');
    for (i=0;i<tables.length;i++) {
        if (!getNodeAttribute(tables[i], 'noselectionbar')) {
            var inputs = tables[i].getElementsByTagName('input');
            var cbs = filter(function(x){return x.type=='checkbox'}, inputs);
            if (cbs.length) insertSelBar(tables[i]);
        }
    }
}

function applyBrowserSpecificStyles() {
    if (navigator.userAgent.match('Mac')) {
        var searchform=$("searchform-label");
        setStyle(searchform, {
            'left':'-5em'
        });
    }
}

var removeAutoComplete = function(el) {
    setNodeAttribute(el, 'autocomplete', 'off');
}

var removeElementAutoCompletes = function() {
    var inputs = $$('input');
    map(removeAutoComplete, inputs);
}

addLoadEvent(removeElementAutoCompletes);
addLoadEvent(applyBrowserSpecificStyles);
addLoadEvent(addSelectionBar);
addLoadEvent(checkForCollapsed);


postJSONDoc = function (url, postVars) {
        var req = getXMLHttpRequest();
        req.open("POST", url, true);
        req.setRequestHeader("Content-type", 
                             "application/x-www-form-urlencoded");
        var data = queryString(postVars);
        var d = sendXMLHttpRequest(req, data);
        return d.addCallback(evalJSONRequest);

}

var cancelWithTimeout = function (deferred, timeout) { 
    var canceller = callLater(timeout, function () { 
        // cancel the deferred after timeout seconds 
        deferred.cancel(); 
        //log("cancel load data")
    }); 
    return deferred.addCallback(function (res) { 
        // if the deferred fires successfully, cancel the timeout 
        canceller.cancel(); 
        return res; 
    }); 
};

function handle(delta) {
	if (delta < 0)
		/* something. */;
	else
		/* something. */;
}

function wheel(event){
	var delta = 0;
	if (!event) event = window.event;
	if (event.wheelDelta) {
		delta = event.wheelDelta/120; 
		if (window.opera) delta = -delta;
	} else if (event.detail) {
		delta = -event.detail/3;
	}
	if (delta)
		handle(delta);
       if (event.preventDefault)
           event.preventDefault();
       event.returnValue = false;
}

function captureSubmit(e){
    switch (e.key().string) {
        case 'KEY_ENTER':
            var submit = $('dialog_submit');
            submit.click();
            return;
        default:
    }
}


function checkValidId(e){
    var errmsg = $('errmsg');
    var input = $('new_id');
    var label = $('new_id_label');
    var new_id = escape(input.value);
    var submit = $('dialog_submit');
    var path = $('checkValidIdPath').value
    
    errmsg.innerHTML = "";
    Morph(input, {"style": {"color": "black"}});
    Morph(label, {"style": {"color": "white"}});
    
    d = callLater(0, doXHR, path+'/checkValidId', {queryString:{'id':new_id}});
    d.addCallback(function (r) { 
        if (r.responseText == 'True') { 
            submit.disabled = false;
            if (e && e.key().string == 'KEY_ENTER') submit.click();
        } else {
            submit.disabled = true;
            Morph(input, {"style": {"color": "red"}});
            Morph(label, {"style": {"color": "red"}});
            errmsg.innerHTML = r.responseText;
            shake(input);
            shake(label);
            shake(errmsg);
        }   
    });
}

function connectTextareas() {

    var vDims, vPos, aDims, aPos, rightedge_area, rightedge_vp;

    var refreshVars = function() {
        vDims = getViewportDimensions();
        vPos = getViewportPosition();
        rightedge_vp = vDims.w + vPos.x;
        var area = $$('textarea')[0];
        aDims = getElementDimensions(area);
        aPos = getElementPosition(area);
        rightedge_area = aDims.w + aPos.x;
    }

    function resizeAll() {
        refreshVars();
        map(resizeArea, $$('textarea'));
    }

    function resizeArea(area) {
        var w = aDims.w + rightedge_vp-rightedge_area-50;
        setElementDimensions(area, {w:w});
    }

    connect(currentWindow(), 'onresize', function(e) {
        map(resizeAll, $$('textarea'));
    });

    map(resizeAll, $$('textarea'));
}


ImagePreloader = Class.create();
ImagePreloader.prototype = {
    __init__: function() {
        bindMethods(this);
        this.buffer = new Image(25, 25);
        this.queue = new Array();
        this.lock = new DeferredLock();
    },
    add: function(img) {
        this.queue.push(img);
        this.start();
    },
    start: function() {
        var d = this.lock.acquire();
        d.addCallback(this.next);
    },
    next: function() {
        var img = this.queue.pop();
        if (img) this.buffer.src = img;
        this.lock.release();
    }
}

/* MENUS */
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
    var isIE//@cc_on=1
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
    if (isIE && $(menu).className!='devmovemenuitems') finalDims.y += 10;
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
    try {
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
    } catch(e) {noop()};
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


/* ZGDAgent */

function notifyParentOfNewUrl() {
    try {
          var parwin = currentWindow().parent;
          var url = location.href;
          parwin.zmlistener.checkForDomainChange(url);
        } 
    catch(e){ noop() }
}

addLoadEvent(notifyParentOfNewUrl);

/* Selection stuff */
var checkboxes;
var currentCheckbox;
var isCheckbox = function(elem) { 
    return (elem.type=='checkbox') }

function getCheckboxes(elem) {
    var inputs = getElementsByTagAndClassName('input', null);
    return filter(isCheckbox, inputs);
}

function selectCheckboxRange(start, end) {
    a = end>start?start:end;
    b = start==a?end:start;
    newstate = -checkboxes[end].checked;
    var todo = checkboxes.slice(a, b+1);
    for (i=0;(box=todo[i]);i++) {
        if ((!box.checked && newstate) ||
            (box.checked && !newstate)) box.click();
        //box.checked = newstate;
    }
}

function getIndex(box) {
    return findIdentical(checkboxes, box);
}

function handleChange(e) {
    var t = e.src();
    var shift = e.modifier().shift;
    if (isCheckbox(t) && shift) {
        if (currentCheckbox){
            selectCheckboxRange(
            getIndex(currentCheckbox), getIndex(t));
            currentCheckbox = t;
        }
    }
    currentCheckbox = t;
}

var CbCxs = new Array();
function connectCheckboxListeners() {
    disconnectAllTo(handleChange);
    checkboxes = getCheckboxes();
    for (i=0; i<checkboxes.length; i++){
        var box = checkboxes[i];
        connect(box, 'onkeypress', handleChange);
        connect(box, 'onclick', handleChange);
    }
}

addLoadEvent(connectCheckboxListeners);

/* zenmodelfuncs */

function zenPageInit(){

    var as = $$('#leftPane a');
    for(var i=0; i< as.length; i++){
        if (location.href.indexOf('notabs') != -1 && 
            location.href==as[i].href) {
                as[i].className = 'selected';
        }
        else if( location.href.indexOf('notabs')==-1 && 
                 as[i].href.indexOf('notabs')==-1 &&
                 location.pathname.indexOf(as[i].pathname) != -1){
            as[i].className = 'selected';
            //lastLeft = as[i];
        }
        else {
            as[i].className = 'unselected';
        }
    }
}

function submitAction(myform, url) {
    myform.action=url
    myform.submit()
}

function submitViaEnter(evt, submitName) {
    evt = (evt) ? evt : event;
    var target = (evt.target) ? evt.target : evt.srcElement;
    var form = target.form;
    var charCode = (evt.charCode) ? evt.charCode : 
        ((evt.which) ? evt.which : evt.keyCode);
    if (charCode == 13 || charCode == 3) {
        if (submitName) { form.action += "/" + submitName }
        form.submit();
        return false;
    }
    return true;
}

function blockSubmitViaEnter(evt) {
    evt = (evt) ? evt : event;
    var charCode = (evt.charCode) ? evt.charCode : 
        ((evt.which) ? evt.which : evt.keyCode);
    if (charCode == 13 || charCode == 3) {
        return false;
    }
    return true;
}

isSelected = false;

function toggleSelect(form) {
    if (isSelected == false) {
        for (i = 0; i < form.length; i++) {
            if (form.elements[i].name == "negateFilter") { continue }
            form.elements[i].checked = true ;
        }
        isSelected = true;
        form.SelectButton.value = "Deselect All";
        return isSelected;
    }
    else {
        for (i = 0; i < form.length; i++) {
            if (form.elements[i].name == "negateFilter") { continue }
            form.elements[i].checked = false ;
        }
        isSelected = false;
        form.SelectButton.value = "Select All";
        return isSelected;       
    }
}

addLoadEvent(zenPageInit)
