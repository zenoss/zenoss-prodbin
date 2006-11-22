/** FormCollect - Compiles a string of form data. - brad@xkr.us - 2004-10-20 **
 ** Code licensed under Creative Commons Attribution-ShareAlike License      **
 ** http://creativecommons.org/licenses/by-sa/2.0/                           **/
function FormCollect(oForm)
{
  var sRetval='', sTemp='', sCTName='', sCName='', sCType='', arrElts=[],
    oCurrent=null;
  for (var i=oForm.elements.length-1; i >= 0; i--)
  {
    oCurrent = oForm.elements[i];
    /* successful elements must have a name and must not be disabled */
    if (oCurrent.name && !oCurrent.disabled) arrElts.push(oCurrent);
  }

  /* sort elements so same names will be adjacent to each other */
  arrElts.sort(function(a,b){return ((a.name<b.name)?1:(a.name==b.name)?0:-1);});

  while (oCurrent = arrElts.pop())
  {
    sCTName = oCurrent.tagName.toLowerCase();
    sCName = oCurrent.name.toLowerCase();
    sCType = ((oCurrent.type)?oCurrent.type:'').toLowerCase();

    /* handle input[type="radio|checkbox"] */
    if (sCTName == "input" && /^(?:radio|checkbox)$/.test(sCType))
    {
      do {
        if (oCurrent.checked || oCurrent.selected)
          sRetval = sRetval.append(encodeURIComponent(oCurrent.name) + '=' +
                         encodeURIComponent(oCurrent.value), '&');
      } while (arrElts[arrElts.length-1].name == oCurrent.name &&
               (oCurrent = arrElts.pop()));
    }

    /* handle select[multiple] */
    if (sCTName == "select" && oCurrent.multiple && oCurrent.options)
    {
      for (i=0,len=oCurrent.options.length,sTemp=''; i < len; i++)
        if (oCurrent.options[i].selected)
          sTemp = sTemp.append(encodeURIComponent(oCurrent.options[i].value),
                               ',');
      sRetval = sRetval.append(encodeURIComponent(oCurrent.name) + '=' +
                               sTemp, '&');
    }
    /* any other element */
    else if ((sCTName == "input" &&
             /^(?:text|password|hidden)$/.test(sCType)) ||
            /^(?:select|textarea)$/.test(sCTName))
    {
      sRetval = sRetval.append(encodeURIComponent(oCurrent.name) + '=' +
                     encodeURIComponent(oCurrent.value), '&');
    }
  }
  return sRetval;
}
String.prototype.append = function(sAdd, sSep)
{
  return this + ((this.length)?sSep:'') + sAdd;
}
