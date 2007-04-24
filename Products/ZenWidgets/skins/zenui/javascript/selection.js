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
    log(checkboxes.length+" Checkboxes extant");
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
log("Checkbox javascript loaded.");
