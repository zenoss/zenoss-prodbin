//<script metal:define-macro="submitAction" language="JavaScript">

//----------------------------------------------
// initialize page
//------------------------------------------------

function zenPageInit(){
    // set the state of the leftPane
    // - this is a bit of a hack
    // - it does not change the state of an existing unless it finds
    var as = document.getElementById("leftPane").getElementsByTagName("A");
    for(var i=0; i< as.length; i++){
        if( location.pathname.indexOf(as[i].pathname) != -1){
            as[i].className = 'selected';
            //lastLeft = as[i];
        }
        else {
            as[i].className = 'unselected';
        }
    }
    /*
    var tt = document.getElementById("tabsPane")
    if(tt) {
        tabs = tt.getElementsByTagName("a");
        for(var i=0; i<tabs.length; i++) {
            log("rounding element=",tabs[i]);
            roundElement(tabs[i],{corners:"tl tr"});
        }
    }
    */
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
