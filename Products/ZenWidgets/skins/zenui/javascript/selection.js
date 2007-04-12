var checkboxes;
var currentCheckbox;
var isCheckbox = function(elem) { 
    return (elem.type=='checkbox') }

function getCheckboxes() {
    var inputs = getElementsByTagAndClassName('input', null);
    return filter(isCheckbox, inputs);
}

function selectCheckboxRange(start, end) {
    a = end>start?start:end;
    b = start==a?end:start;
    newstate = -checkboxes[end].checked;
    var todo = checkboxes.slice(a, b+1);
    for (i=0;(box=todo[i]);i++) {
        box.checked = newstate;
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

function connectCheckboxListeners() {
checkboxes = getCheckboxes();
    for (i=0; i<checkboxes.length; i++){
        var box = checkboxes[i];
        connect(box, 'onkeypress', handleChange);
        disconnectAll(box, 'onclick');
        connect(box, 'onclick', handleChange);
    }
}

addLoadEvent(connectCheckboxListeners);
log("Checkbox javascript loaded.");
