/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */var dj_global=this;
function dj_undef(_1,_2){
if(!_2){
_2=dj_global;
}
return (typeof _2[_1]=="undefined");
}
function dj_eval_object_path(_3,_4){
if(typeof _3!="string"){
return dj_global;
}
if(_3.indexOf(".")==-1){
return dj_undef(_3)?undefined:dj_global[_3];
}
var _5=_3.split(/\./);
var _6=dj_global;
for(var i=0;i<_5.length;++i){
if(!_4){
_6=_6[_5[i]];
if((typeof _6=="undefined")||(!_6)){
return _6;
}
}else{
if(dj_undef(_5[i],_6)){
_6[_5[i]]={};
}
_6=_6[_5[i]];
}
}
return _6;
}
if(dj_undef("djConfig")){
var djConfig={};
}
var dojo;
if(dj_undef("dojo")){
dojo={};
}
dojo.version={major:0,minor:1,patch:0,revision:Number("$Rev: 1321 $".match(/[0-9]+/)[0]),toString:function(){
var v=dojo.version;
return v.major+"."+v.minor+"."+v.patch+" ("+v.revision+")";
}};
function dj_error_to_string(_9){
return ((!dj_undef("message",_9))?_9.message:(dj_undef("description",_9)?_9:_9.description));
}
function dj_debug(){
var _10=arguments;
if(dj_undef("println",dojo.hostenv)){
dj_throw("dj_debug not available (yet?)");
}
if(!dojo.hostenv.is_debug_){
return;
}
var _11=dj_global["jum"];
var s=_11?"":"DEBUG: ";
for(var i=0;i<_10.length;++i){
if(!false&&_10[i] instanceof Error){
var msg="["+_10[i].name+": "+dj_error_to_string(_10[i])+(_10[i].fileName?", file: "+_10[i].fileName:"")+(_10[i].lineNumber?", line: "+_10[i].lineNumber:"")+"]";
}else{
var msg=_10[i];
}
s+=msg+" ";
}
if(_11){
jum.debug(s);
}else{
dojo.hostenv.println(s);
}
}
function dj_throw(_14){
var he=dojo.hostenv;
if(dj_undef("hostenv",dojo)&&dj_undef("println",dojo)){
dojo.hostenv.println("FATAL: "+_14);
}
throw Error(_14);
}
function dj_rethrow(_16,_17){
var _18=dj_error_to_string(_17);
dj_throw(_16+": "+_18);
}
function dj_eval(s){
return dj_global.eval?dj_global.eval(s):eval(s);
}
function dj_unimplemented(_19,_20){
var _21="'"+_19+"' not implemented";
if((typeof _20!="undefined")&&(_20)){
_21+=" "+_20;
}
dj_throw(_21);
}
function dj_deprecated(_22,_23){
var _24="DEPRECATED: "+_22;
if((typeof _23!="undefined")&&(_23)){
_24+=" "+_23;
}
dj_debug(_24);
}
function dj_inherits(_25,_26){
if(typeof _26!="function"){
dj_throw("superclass: "+_26+" borken");
}
_25.prototype=new _26();
_25.prototype.constructor=_25;
_25.superclass=_26.prototype;
_25["super"]=_26.prototype;
}
dojo.render={name:"",ver:dojo.version,os:{win:false,linux:false,osx:false},html:{capable:false,support:{builtin:false,plugin:false},ie:false,opera:false,khtml:false,safari:false,moz:false,prefixes:["html"]},svg:{capable:false,support:{builtin:false,plugin:false},corel:false,adobe:false,batik:false,prefixes:["svg"]},swf:{capable:false,support:{builtin:false,plugin:false},mm:false,prefixes:["Swf","Flash","Mm"]},swt:{capable:false,support:{builtin:false,plugin:false},ibm:false,prefixes:["Swt"]}};
dojo.hostenv=(function(){
var djc=djConfig;
function _def(obj,_29,def){
return (dj_undef(_29,obj)?def:obj[_29]);
}
return {is_debug_:_def(djc,"isDebug",false),base_script_uri_:_def(djc,"baseScriptUri",undefined),base_relative_path_:_def(djc,"baseRelativePath",""),library_script_uri_:_def(djc,"libraryScriptUri",""),auto_build_widgets_:_def(djc,"parseWidgets",true),ie_prevent_clobber_:_def(djc,"iePreventClobber",false),ie_clobber_minimal_:_def(djc,"ieClobberMinimal",false),name_:"(unset)",version_:"(unset)",pkgFileName:"__package__",loading_modules_:{},loaded_modules_:{},addedToLoadingCount:[],removedFromLoadingCount:[],inFlightCount:0,modulePrefixes_:{dojo:{name:"dojo",value:"src"}},setModulePrefix:function(_31,_32){
this.modulePrefixes_[_31]={name:_31,value:_32};
},getModulePrefix:function(_33){
var mp=this.modulePrefixes_;
if((mp[_33])&&(mp[_33]["name"])){
return mp[_33].value;
}
return _33;
},getTextStack:[],loadUriStack:[],loadedUris:[],modules_:{},modulesLoadedFired:false,modulesLoadedListeners:[],getName:function(){
return this.name_;
},getVersion:function(){
return this.version_;
},getText:function(uri){
dj_unimplemented("getText","uri="+uri);
},getLibraryScriptUri:function(){
dj_unimplemented("getLibraryScriptUri","");
}};
})();
dojo.hostenv.getBaseScriptUri=function(){
if(!dj_undef("base_script_uri_",this)){
return this.base_script_uri_;
}
var uri=this.library_script_uri_;
if(!uri){
uri=this.library_script_uri_=this.getLibraryScriptUri();
if(!uri){
dj_throw("Nothing returned by getLibraryScriptUri(): "+uri);
}
}
var _36=uri.lastIndexOf("/");
this.base_script_uri_=this.base_relative_path_;
return this.base_script_uri_;
};
dojo.hostenv.setBaseScriptUri=function(uri){
this.base_script_uri_=uri;
};
dojo.hostenv.loadPath=function(_37,_38,cb){
if(!_37){
dj_throw("Missing relpath argument");
}
if((_37.charAt(0)=="/")||(_37.match(/^\w+:/))){
dj_throw("relpath '"+_37+"'; must be relative");
}
var uri=this.getBaseScriptUri()+_37;
try{
return ((!_38)?this.loadUri(uri):this.loadUriAndCheck(uri,_38));
}
catch(e){
if(dojo.hostenv.is_debug_){
dj_debug(e);
}
return false;
}
};
dojo.hostenv.loadUri=function(uri,cb){
if(dojo.hostenv.loadedUris[uri]){
return;
}
var _40=this.getText(uri,null,true);
if(_40==null){
return 0;
}
var _41=dj_eval(_40);
return 1;
};
dojo.hostenv.getDepsForEval=function(_42){
if(!_42){
_42="";
}
var _43=[];
var tmp=_42.match(/dojo.hostenv.loadModule\(.*?\)/mg);
if(tmp){
for(var x=0;x<tmp.length;x++){
_43.push(tmp[x]);
}
}
tmp=_42.match(/dojo.hostenv.require\(.*?\)/mg);
if(tmp){
for(var x=0;x<tmp.length;x++){
_43.push(tmp[x]);
}
}
tmp=_42.match(/dojo.require\(.*?\)/mg);
if(tmp){
for(var x=0;x<tmp.length;x++){
_43.push(tmp[x]);
}
}
tmp=_42.match(/dojo.hostenv.conditionalLoadModule\([\w\W]*?\)/gm);
if(tmp){
for(var x=0;x<tmp.length;x++){
_43.push(tmp[x]);
}
}
return _43;
};
dojo.hostenv.loadUriAndCheck=function(uri,_46,cb){
var ok=true;
try{
ok=this.loadUri(uri,cb);
}
catch(e){
dj_debug("failed loading ",uri," with error: ",e);
}
return ((ok)&&(this.findModule(_46,false)))?true:false;
};
dojo.loaded=function(){
};
dojo.hostenv.loaded=function(){
this.modulesLoadedFired=true;
var mll=this.modulesLoadedListeners;
for(var x=0;x<mll.length;x++){
mll[x]();
}
dojo.loaded();
};
dojo.addOnLoad=function(obj,_49){
if(arguments.length==1){
dojo.hostenv.modulesLoadedListeners.push(obj);
}else{
if(arguments.length>1){
dojo.hostenv.modulesLoadedListeners.push(function(){
obj[_49]();
});
}
}
};
dojo.hostenv.modulesLoaded=function(){
if(this.modulesLoadedFired){
return;
}
if((this.loadUriStack.length==0)&&(this.getTextStack.length==0)){
if(this.inFlightCount>0){
dj_debug("couldn't initialize, there are files still in flight");
return;
}
this.loaded();
}
};
dojo.hostenv.moduleLoaded=function(_50){
var _51=dj_eval_object_path((_50.split(".").slice(0,-1)).join("."));
this.loaded_modules_[(new String(_50)).toLowerCase()]=_51;
};
dojo.hostenv.loadModule=function(_52,_53,_54){
var _55=this.findModule(_52,false);
if(_55){
return _55;
}
if(dj_undef(_52,this.loading_modules_)){
this.addedToLoadingCount.push(_52);
}
this.loading_modules_[_52]=1;
var _56=_52.replace(/\./g,"/")+".js";
var _57=_52.split(".");
var _58=_52.split(".");
for(var i=_57.length-1;i>0;i--){
var _59=_57.slice(0,i).join(".");
var _60=this.getModulePrefix(_59);
if(_60!=_59){
_57.splice(0,i,_60);
break;
}
}
var _61=_57[_57.length-1];
if(_61=="*"){
_52=(_58.slice(0,-1)).join(".");
while(_57.length){
_57.pop();
_57.push(this.pkgFileName);
_56=_57.join("/")+".js";
if(_56.charAt(0)=="/"){
_56=_56.slice(1);
}
ok=this.loadPath(_56,((!_54)?_52:null));
if(ok){
break;
}
_57.pop();
}
}else{
_56=_57.join("/")+".js";
_52=_58.join(".");
var ok=this.loadPath(_56,((!_54)?_52:null));
if((!ok)&&(!_53)){
_57.pop();
while(_57.length){
_56=_57.join("/")+".js";
ok=this.loadPath(_56,((!_54)?_52:null));
if(ok){
break;
}
_57.pop();
_56=_57.join("/")+"/"+this.pkgFileName+".js";
if(_56.charAt(0)=="/"){
_56=_56.slice(1);
}
ok=this.loadPath(_56,((!_54)?_52:null));
if(ok){
break;
}
}
}
if((!ok)&&(!_54)){
dj_throw("Could not load '"+_52+"'; last tried '"+_56+"'");
}
}
if(!_54){
_55=this.findModule(_52,false);
if(!_55){
dj_throw("symbol '"+_52+"' is not defined after loading '"+_56+"'");
}
}
return _55;
};
function dj_load(_62,_63){
return dojo.hostenv.loadModule(_62,_63);
}
dojo.hostenv.startPackage=function(_64){
var _65=_64.split(/\./);
if(_65[_65.length-1]=="*"){
_65.pop();
}
return dj_eval_object_path(_65.join("."),true);
};
dojo.hostenv.findModule=function(_66,_67){
if(!dj_undef(_66,this.modules_)){
return this.modules_[_66];
}
if(this.loaded_modules_[(new String(_66)).toLowerCase()]){
return this.loaded_modules_[_66];
}
var _68=dj_eval_object_path(_66);
if((typeof _68!=="undefined")&&(_68)){
return this.modules_[_66]=_68;
}
if(_67){
dj_throw("no loaded module named '"+_66+"'");
}
return null;
};
dj_addNodeEvtHdlr=function(_69,_70,fp,_72){
if(_69.attachEvent){
_69.attachEvent("on"+_70,fp);
}else{
if(_69.addEventListener){
_69.addEventListener(_70,fp,_72);
}else{
var _73=_69["on"+_70];
if(typeof _73!="undefined"){
_69["on"+_70]=function(){
fp.apply(_69,arguments);
_73.apply(_69,arguments);
};
}else{
_69["on"+_70]=fp;
}
}
}
return true;
};
if(typeof window=="undefined"){
dj_throw("no window object");
}
(function(){
if((dojo.hostenv["base_script_uri_"]==""||dojo.hostenv["base_relative_path_"]=="")&&document&&document.getElementsByTagName){
var _74=document.getElementsByTagName("script");
var _75=/(__package__|dojo)\.js$/i;
for(var i=0;i<_74.length;i++){
var src=_74[i].getAttribute("src");
if(_75.test(src)){
var _77=src.replace(_75,"");
if(dojo.hostenv["base_script_uri_"]==""){
dojo.hostenv["base_script_uri_"]=_77;
}
if(dojo.hostenv["base_relative_path_"]==""){
dojo.hostenv["base_relative_path_"]=_77;
}
break;
}
}
}
})();
with(dojo.render){
html.UA=navigator.userAgent;
html.AV=navigator.appVersion;
html.capable=true;
html.support.builtin=true;
ver=parseFloat(html.AV);
os.mac=html.AV.indexOf("Macintosh")==-1?false:true;
os.win=html.AV.indexOf("Windows")==-1?false:true;
html.opera=html.UA.indexOf("Opera")==-1?false:true;
html.khtml=((html.AV.indexOf("Konqueror")>=0)||(html.AV.indexOf("Safari")>=0))?true:false;
html.safari=(html.AV.indexOf("Safari")>=0)?true:false;
html.mozilla=html.moz=((html.UA.indexOf("Gecko")>=0)&&(!html.khtml))?true:false;
html.ie=((document.all)&&(!html.opera))?true:false;
html.ie50=html.ie&&html.AV.indexOf("MSIE 5.0")>=0;
html.ie55=html.ie&&html.AV.indexOf("MSIE 5.5")>=0;
html.ie60=html.ie&&html.AV.indexOf("MSIE 6.0")>=0;
}
dojo.hostenv.startPackage("dojo.hostenv");
dojo.hostenv.name_="browser";
dojo.hostenv.searchIds=[];
var DJ_XMLHTTP_PROGIDS=["Msxml2.XMLHTTP","Microsoft.XMLHTTP","Msxml2.XMLHTTP.4.0"];
dojo.hostenv.getXmlhttpObject=function(){
var _78=null;
var _79=null;
try{
_78=new XMLHttpRequest();
}
catch(e){
}
if(!_78){
for(var i=0;i<3;++i){
var _80=DJ_XMLHTTP_PROGIDS[i];
try{
_78=new ActiveXObject(_80);
}
catch(e){
_79=e;
}
if(_78){
DJ_XMLHTTP_PROGIDS=[_80];
break;
}
}
}
if((_79)&&(!_78)){
dj_rethrow("Could not create a new ActiveXObject using any of the progids "+DJ_XMLHTTP_PROGIDS.join(", "),_79);
}else{
if(!_78){
return dj_throw("No XMLHTTP implementation available, for uri "+uri);
}
}
return _78;
};
dojo.hostenv.getText=function(uri,_81,_82){
var _83=this.getXmlhttpObject();
if(_81){
_83.onreadystatechange=function(){
if((4==_83.readyState)&&(_83["status"])){
if(_83.status==200){
dj_debug("LOADED URI: "+uri);
_81(_83.responseText);
}
}
};
}
_83.open("GET",uri,_81?true:false);
_83.send(null);
if(_81){
return null;
}
return _83.responseText;
};
function dj_last_script_src(){
var _84=window.document.getElementsByTagName("script");
if(_84.length<1){
dj_throw("No script elements in window.document, so can't figure out my script src");
}
var _85=_84[_84.length-1];
var src=_85.src;
if(!src){
dj_throw("Last script element (out of "+_84.length+") has no src");
}
return src;
}
if(!dojo.hostenv["library_script_uri_"]){
dojo.hostenv.library_script_uri_=dj_last_script_src();
}
dojo.hostenv.println=function(s){
var ti=null;
var dis="<div>"+s+"</div>";
try{
ti=document.createElement("div");
document.body.appendChild(ti);
ti.innerHTML=s;
}
catch(e){
try{
document.write(dis);
}
catch(e2){
window.status=s;
}
}
delete ti;
delete dis;
delete s;
};
dj_addNodeEvtHdlr(window,"load",function(){
if(dojo.render.html.ie){
dojo.hostenv.makeWidgets();
}
dojo.hostenv.modulesLoaded();
});
dojo.hostenv.makeWidgets=function(){
if((dojo.hostenv.auto_build_widgets_)||(dojo.hostenv.searchIds.length>0)){
if(dj_eval_object_path("dojo.widget.Parse")){
try{
var _88=new dojo.xml.Parse();
var _89=dojo.hostenv.searchIds;
if(_89.length>0){
for(var x=0;x<_89.length;x++){
if(!document.getElementById(_89[x])){
continue;
}
var _90=_88.parseElement(document.getElementById(_89[x]),null,true);
dojo.widget.getParser().createComponents(_90);
}
}else{
if(dojo.hostenv.auto_build_widgets_){
var _90=_88.parseElement(document.body,null,true);
dojo.widget.getParser().createComponents(_90);
}
}
}
catch(e){
dj_debug("auto-build-widgets error:",e);
}
}
}
};
dojo.hostenv.modulesLoadedListeners.push(function(){
if(!dojo.render.html.ie){
dojo.hostenv.makeWidgets();
}
});
if((!window["djConfig"])||(!window["djConfig"]["preventBackButtonFix"])){
document.write("<iframe style='border: 0px; width: 1px; height: 1px; position: absolute; bottom: 0px; right: 0px; visibility: visible;' name='djhistory' id='djhistory' src='"+(dojo.hostenv.getBaseScriptUri()+"iframe_history.html")+"'></iframe>");
}
dojo.hostenv.writeIncludes=function(){
};
dojo.hostenv.conditionalLoadModule=function(_91){
var _92=_91["common"]||[];
var _93=(_91[dojo.hostenv.name_])?_92.concat(_91[dojo.hostenv.name_]||[]):_92.concat(_91["default"]||[]);
for(var x=0;x<_93.length;x++){
var _94=_93[x];
if(_94.constructor==Array){
dojo.hostenv.loadModule.apply(dojo.hostenv,_94);
}else{
dojo.hostenv.loadModule(_94);
}
}
};
dojo.hostenv.require=dojo.hostenv.loadModule;
dojo.require=function(){
dojo.hostenv.loadModule.apply(dojo.hostenv,arguments);
};
dojo.requireIf=function(){
if((arguments[0]=="common")||(dojo.render[arguments[0]].capable)){
dojo.require(arguments[1],arguments[2],arguments[3]);
}
};
dojo.conditionalRequire=dojo.requireIf;
dojo.kwCompoundRequire=function(){
dojo.hostenv.conditionalLoadModule.apply(dojo.hostenv,arguments);
};
dojo.hostenv.provide=dojo.hostenv.startPackage;
dojo.provide=function(){
dojo.hostenv.startPackage.apply(dojo.hostenv,arguments);
};
dojo.provide("dojo.io.IO");
dojo.io.transports=[];
dojo.io.hdlrFuncNames=["load","error"];
dojo.io.Request=function(url,mt,_97,_98){
this.url=url;
this.mimetype=mt;
this.transport=_97;
this.changeUrl=_98;
this.formNode=null;
this.events_={};
var _99=this;
this.error=function(type,_101){
switch(type){
case "io":
var _102=dojo.io.IOEvent.IO_ERROR;
var _103="IOError: error during IO";
break;
case "parse":
var _102=dojo.io.IOEvent.PARSE_ERROR;
var _103="IOError: error during parsing";
default:
var _102=dojo.io.IOEvent.UNKOWN_ERROR;
var _103="IOError: cause unkown";
}
var _104=new dojo.io.IOEvent("error",null,_99,_103,this.url,_102);
_99.dispatchEvent(_104);
if(_99.onerror){
_99.onerror(_103,_99.url,_104);
}
};
this.load=function(type,data,evt){
var _107=new dojo.io.IOEvent("load",data,_99,null,null,null);
_99.dispatchEvent(_107);
if(_99.onload){
_99.onload(_107);
}
};
this.backButton=function(){
var _108=new dojo.io.IOEvent("backbutton",null,_99,null,null,null);
_99.dispatchEvent(_108);
if(_99.onbackbutton){
_99.onbackbutton(_108);
}
};
this.forwardButton=function(){
var _109=new dojo.io.IOEvent("forwardbutton",null,_99,null,null,null);
_99.dispatchEvent(_109);
if(_99.onforwardbutton){
_99.onforwardbutton(_109);
}
};
};
dojo.io.Request.prototype.addEventListener=function(type,func){
if(!this.events_[type]){
this.events_[type]=[];
}
for(var i=0;i<this.events_[type].length;i++){
if(this.events_[type][i]==func){
return;
}
}
this.events_[type].push(func);
};
dojo.io.Request.prototype.removeEventListener=function(type,func){
if(!this.events_[type]){
return;
}
for(var i=0;i<this.events_[type].length;i++){
if(this.events_[type][i]==func){
this.events_[type].splice(i,1);
}
}
};
dojo.io.Request.prototype.dispatchEvent=function(evt){
if(!this.events_[evt.type]){
return;
}
for(var i=0;i<this.events_[evt.type].length;i++){
this.events_[evt.type][i](evt);
}
return false;
};
dojo.io.IOEvent=function(type,data,_111,_112,_113,_114){
this.type=type;
this.data=data;
this.request=_111;
this.errorMessage=_112;
this.errorUrl=_113;
this.errorCode=_114;
};
dojo.io.IOEvent.UNKOWN_ERROR=0;
dojo.io.IOEvent.IO_ERROR=1;
dojo.io.IOEvent.PARSE_ERROR=2;
dojo.io.Error=function(msg,type,num){
this.message=msg;
this.type=type||"unknown";
this.number=num||0;
};
dojo.io.transports.addTransport=function(name){
this.push(name);
this[name]=dojo.io[name];
};
dojo.io.bind=function(_117){
if(!_117["url"]){
_117.url="";
}else{
_117.url=_117.url.toString();
}
if(!_117["mimetype"]){
_117.mimetype="text/plain";
}
if(!_117["method"]&&!_117["formNode"]){
_117.method="get";
}else{
if(_117["formNode"]){
_117.method=_117["method"]||_117["formNode"].method||"get";
}
}
if(_117["handler"]){
_117.handle=_117.handler;
}
if(!_117["handle"]){
_117.handle=function(){
};
}
if(_117["loaded"]){
_117.load=_117.loaded;
}
if(_117["changeUrl"]){
_117.changeURL=_117.changeUrl;
}
for(var x=0;x<this.hdlrFuncNames.length;x++){
var fn=this.hdlrFuncNames[x];
if(typeof _117[fn]=="function"){
continue;
}
if(typeof _117.handler=="object"){
if(typeof _117.handler[fn]=="function"){
_117[fn]=_117.handler[fn]||_117.handler["handle"]||function(){
};
}
}else{
if(typeof _117["handler"]=="function"){
_117[fn]=_117.handler;
}else{
if(typeof _117["handle"]=="function"){
_117[fn]=_117.handle;
}
}
}
}
var _119="";
if(_117["transport"]){
_119=_117["transport"];
if(!this[_119]){
return false;
}
}else{
for(var x=0;x<dojo.io.transports.length;x++){
var tmp=dojo.io.transports[x];
if((this[tmp])&&(this[tmp].canHandle(_117))){
_119=tmp;
}
}
if(_119==""){
return false;
}
}
this[_119].bind(_117);
return true;
};
dojo.io.argsFromMap=function(map){
var _121=new Object();
var _122="";
for(var x in map){
if(!_121[x]){
_122+=encodeURIComponent(x)+"="+encodeURIComponent(map[x])+"&";
}
}
return _122;
};
dojo.provide("dojo.alg.Alg");
dojo.alg.find=function(arr,val){
for(var i=0;i<arr.length;++i){
if(arr[i]==val){
return i;
}
}
return -1;
};
dojo.alg.inArray=function(arr,val){
if((!arr||arr.constructor!=Array)&&(val&&val.constructor==Array)){
var a=arr;
arr=val;
val=a;
}
return dojo.alg.find(arr,val)>-1;
};
dojo.alg.inArr=dojo.alg.inArray;
dojo.alg.getNameInObj=function(ns,item){
if(!ns){
ns=dj_global;
}
for(var x in ns){
if(ns[x]===item){
return new String(x);
}
}
return null;
};
dojo.alg.has=function(obj,name){
return (typeof obj[name]!=="undefined");
};
dojo.alg.forEach=function(arr,_128,_129){
var il=arr.length;
for(var i=0;i<((_129)?il:arr.length);i++){
if(_128(arr[i])=="break"){
break;
}
}
};
dojo.alg.for_each=dojo.alg.forEach;
dojo.alg.map=function(arr,obj,_131){
for(var i=0;i<arr.length;++i){
_131.call(obj,arr[i]);
}
};
dojo.alg.tryThese=function(){
for(var x=0;x<arguments.length;x++){
try{
if(typeof arguments[x]=="function"){
var ret=(arguments[x]());
if(ret){
return ret;
}
}
}
catch(e){
dj_debug(e);
}
}
};
dojo.alg.delayThese=function(farr,cb,_134,_135){
if(!farr.length){
if(typeof _135=="function"){
_135();
}
return;
}
if((typeof _134=="undefined")&&(typeof cb=="number")){
_134=cb;
cb=function(){
};
}else{
if(!cb){
cb=function(){
};
}
}
setTimeout(function(){
(farr.shift())();
cb();
dojo.alg.delayThese(farr,cb,_134,_135);
},_134);
};
dojo.alg.for_each_call=dojo.alg.map;
dojo.require("dojo.alg.Alg",false,true);
dojo.hostenv.moduleLoaded("dojo.alg.*");
dojo.provide("dojo.io.BrowserIO");
dojo.require("dojo.io.IO");
dojo.require("dojo.alg.*");
dojo.io.checkChildrenForFile=function(node){
var _137=false;
var _138=node.getElementsByTagName("input");
dojo.alg.forEach(_138,function(_139){
if(_137){
return;
}
if(_139.getAttribute("type")=="file"){
_137=true;
}
});
return _137;
};
dojo.io.formHasFile=function(_140){
return dojo.io.checkChildrenForFile(_140);
};
dojo.io.encodeForm=function(_141){
if((!_141)||(!_141.tagName)||(!_141.tagName.toLowerCase()=="form")){
dj_throw("Attempted to encode a non-form element.");
}
var ec=encodeURIComponent;
var _143=[];
for(var i=0;i<_141.elements.length;i++){
var elm=_141.elements[i];
if(elm.disabled){
continue;
}
var name=ec(elm.name);
var type=elm.type.toLowerCase();
if((type=="select")&&(elm.multiple)){
for(var j=0;j<elm.options.length;j++){
_143.push(name+"="+ec(elm.options[j].value));
}
}else{
if(dojo.alg.inArray(type,["radio","checked"])){
if(elm.checked){
_143.push(name+"="+ec(elm.value));
}
}else{
if(!dojo.alg.inArray(type,["file","submit","reset","button"])){
_143.push(name+"="+ec(elm.value));
}
}
}
}
return _143.join("&");
};
dojo.io.setIFrameSrc=function(_146,src,_147){
try{
var r=dojo.render.html;
if(!_147){
if(r.safari){
_146.location=src;
}else{
frames[_146.name].location=src;
}
}else{
var idoc=(r.moz)?_146.contentWindow:_146;
idoc.location.replace(src);
dj_debug(_146.contentWindow.location);
}
}
catch(e){
dj_debug("setIFrameSrc: "+e);
}
};
dojo.io.createIFrame=function(_150){
if(window[_150]){
return window[_150];
}
if(window.frames[_150]){
return window.frames[_150];
}
var r=dojo.render.html;
var _151=null;
_151=document.createElement((((r.ie)&&(r.win))?"<iframe name="+_150+">":"iframe"));
with(_151){
name=_150;
setAttribute("name",_150);
id=_150;
}
window[_150]=_151;
document.body.appendChild(_151);
with(_151.style){
position="absolute";
left=top="0px";
height=width="1px";
visibility="hidden";
if(dojo.hostenv.is_debug_){
position="relative";
height="100px";
width="300px";
visibility="visible";
}
}
dojo.io.setIFrameSrc(_151,dojo.hostenv.getBaseScriptUri()+"iframe_history.html",true);
return _151;
};
dojo.io.cancelDOMEvent=function(evt){
if(!evt){
return false;
}
if(evt.preventDefault){
evt.stopPropagation();
evt.preventDefault();
}else{
if(window.event){
window.event.cancelBubble=true;
window.event.returnValue=false;
}
}
return false;
};
dojo.io.XMLHTTPTransport=new function(){
var _152=this;
this.initialHref=window.location.href;
this.initialHash=window.location.hash;
this.moveForward=false;
var _153={};
this.useCache=false;
this.historyStack=[];
this.forwardStack=[];
this.historyIframe=null;
this.bookmarkAnchor=null;
this.locationTimer=null;
function getCacheKey(url,_154,_155){
return url+"|"+_154+"|"+_155.toLowerCase();
}
function addToCache(url,_156,_157,http){
_153[getCacheKey(url,_156,_157)]=http;
}
function getFromCache(url,_159,_160){
return _153[getCacheKey(url,_159,_160)];
}
this.clearCache=function(){
_153={};
};
function doLoad(_161,http,url,_162,_163){
if(http.status==200||(location.protocol=="file:"&&http.status==0)){
var ret;
if(_161.method.toLowerCase()=="head"){
var _164=http.getAllResponseHeaders();
ret={};
ret.toString=function(){
return _164;
};
var _165=_164.split(/[\r\n]+/g);
for(var i=0;i<_165.length;i++){
var pair=_165[i].match(/^([^:]+)\s*:\s*(.+)$/i);
if(pair){
ret[pair[1]]=pair[2];
}
}
}else{
if(_161.mimetype=="text/javascript"){
ret=dj_eval(http.responseText);
}else{
if(_161.mimetype=="text/xml"){
ret=http.responseXML;
if(!ret||typeof ret=="string"){
ret=dojo.xml.domUtil.createDocumentFromText(http.responseText);
}
}else{
ret=http.responseText;
}
}
}
if(_163){
addToCache(url,_162,_161.method,http);
}
if(typeof _161.load=="function"){
_161.load("load",ret,http);
}
}else{
var _167=new dojo.io.Error("XMLHttpTransport Error: "+http.status+" "+http.statusText);
if(typeof _161.error=="function"){
_161.error("error",_167,http);
}
}
}
function setHeaders(http,_168){
if(_168["headers"]){
for(var _169 in _168["headers"]){
if(_169.toLowerCase()=="content-type"&&!_168["contentType"]){
_168["contentType"]=_168["headers"][_169];
}else{
http.setRequestHeader(_169,_168["headers"][_169]);
}
}
}
}
this.addToHistory=function(args){
var _171=args["back"]||args["backButton"]||args["handle"];
var hash=null;
if(!this.historyIframe){
this.historyIframe=window.frames["djhistory"];
}
if(!this.bookmarkAnchor){
this.bookmarkAnchor=document.createElement("a");
document.body.appendChild(this.bookmarkAnchor);
this.bookmarkAnchor.style.display="none";
}
if((!args["changeURL"])||(dojo.render.html.ie)){
var url=dojo.hostenv.getBaseScriptUri()+"iframe_history.html?"+(new Date()).getTime();
this.moveForward=true;
dojo.io.setIFrameSrc(this.historyIframe,url,false);
}
if(args["changeURL"]){
hash="#"+((args["changeURL"]!==true)?args["changeURL"]:(new Date()).getTime());
setTimeout("window.location.href = '"+hash+"';",1);
this.bookmarkAnchor.href=hash;
if(dojo.render.html.ie){
var _173=_171;
var lh=null;
var hsl=this.historyStack.length-1;
if(hsl>=0){
while(!this.historyStack[hsl]["urlHash"]){
hsl--;
}
lh=this.historyStack[hsl]["urlHash"];
}
if(lh){
_171=function(){
if(window.location.hash!=""){
setTimeout("window.location.href = '"+lh+"';",1);
}
_173();
};
}
this.forwardStack=[];
var _176=args["forward"]||args["forwardButton"];
var tfw=function(){
if(window.location.hash!=""){
window.location.href=hash;
}
if(_176){
_176();
}
};
if(args["forward"]){
args.forward=tfw;
}else{
if(args["forwardButton"]){
args.forwardButton=tfw;
}
}
}else{
if(dojo.render.html.moz){
if(!this.locationTimer){
this.locationTimer=setInterval("dojo.io.XMLHTTPTransport.checkLocation();",200);
}
}
}
}
this.historyStack.push({"url":url,"callback":_171,"kwArgs":args,"urlHash":hash});
};
this.checkLocation=function(){
var hsl=this.historyStack.length;
if((window.location.hash==this.initialHash)||(window.location.href==this.initialHref)&&(hsl==1)){
this.handleBackButton();
return;
}
if(this.forwardStack.length>0){
if(this.forwardStack[this.forwardStack.length-1].urlHash==window.location.hash){
this.handleForwardButton();
return;
}
}
if((hsl>=2)&&(this.historyStack[hsl-2])){
if(this.historyStack[hsl-2].urlHash==window.location.hash){
this.handleBackButton();
return;
}
}
};
this.iframeLoaded=function(evt,_178){
var isp=_178.href.split("?");
if(isp.length<2){
if(this.historyStack.length==1){
this.handleBackButton();
}
return;
}
var _180=isp[1];
if(this.moveForward){
this.moveForward=false;
return;
}
var last=this.historyStack.pop();
if(!last){
if(this.forwardStack.length>0){
var next=this.forwardStack[this.forwardStack.length-1];
if(_180==next.url.split("?")[1]){
this.handleForwardButton();
}
}
return;
}
this.historyStack.push(last);
if(this.historyStack.length>=2){
if(isp[1]==this.historyStack[this.historyStack.length-2].url.split("?")[1]){
this.handleBackButton();
}
}else{
this.handleBackButton();
}
};
this.handleBackButton=function(){
var last=this.historyStack.pop();
if(!last){
return;
}
if(last["callback"]){
last.callback();
}else{
if(last.kwArgs["backButton"]){
last.kwArgs["backButton"]();
}else{
if(last.kwArgs["back"]){
last.kwArgs["back"]();
}else{
if(last.kwArgs["handle"]){
last.kwArgs.handle("back");
}
}
}
}
this.forwardStack.push(last);
};
this.handleForwardButton=function(){
var last=this.forwardStack.pop();
if(!last){
return;
}
if(last.kwArgs["forward"]){
last.kwArgs.forward();
}else{
if(last.kwArgs["forwardButton"]){
last.kwArgs.forwardButton();
}else{
if(last.kwArgs["handle"]){
last.kwArgs.handle("forward");
}
}
}
this.historyStack.push(last);
};
var _183=dojo.hostenv.getXmlhttpObject()?true:false;
this.canHandle=function(_184){
return _183&&dojo.alg.inArray(_184["mimetype"],["text/plain","text/html","text/xml","text/javascript"])&&dojo.alg.inArray(_184["method"].toLowerCase(),["post","get","head"])&&!(_184["formNode"]&&dojo.io.formHasFile(_184["formNode"]));
};
this.bind=function(_185){
if(!_185["url"]){
if(!_185["formNode"]&&(_185["backButton"]||_185["back"]||_185["changeURL"]||_185["watchForURL"])&&(!window["djConfig"]&&!window["djConfig"]["preventBackButtonFix"])){
this.addToHistory(_185);
return true;
}
}
var url=_185.url;
var _186="";
if(_185["formNode"]){
var ta=_185.formNode.getAttribute("action");
if((ta)&&(!_185["url"])){
url=ta;
}
var tp=_185.formNode.getAttribute("method");
if((tp)&&(!_185["method"])){
_185.method=tp;
}
_186+=dojo.io.encodeForm(_185.formNode);
}
if(!_185["method"]){
_185.method="get";
}
if(_185["content"]){
_186+=dojo.io.argsFromMap(_185.content);
}
if(_185["postContent"]&&_185.method.toLowerCase()=="post"){
_186=_185.postContent;
}
if(_185["backButton"]||_185["back"]||_185["changeURL"]){
this.addToHistory(_185);
}
var _189=_185["sync"]?false:true;
var _190=_185["useCache"]==true||(this.useCache==true&&_185["useCache"]!=false);
if(_190){
var _191=getFromCache(url,_186,_185.method);
if(_191){
doLoad(_185,_191,url,_186,false);
return;
}
}
var http=dojo.hostenv.getXmlhttpObject();
var _192=false;
if(_189){
http.onreadystatechange=function(){
if(4==http.readyState){
if(_192){
return;
}
_192=true;
doLoad(_185,http,url,_186,_190);
}
};
}
if(_185.method.toLowerCase()=="post"){
http.open("POST",url,_189);
setHeaders(http,_185);
http.setRequestHeader("Content-Type",_185["contentType"]||"application/x-www-form-urlencoded");
http.send(_186);
}else{
var _193=url;
if(_186!=""){
_193+=(url.indexOf("?")>-1?"&":"?")+_186;
}
http.open(_185.method.toUpperCase(),_193,_189);
setHeaders(http,_185);
http.send(null);
}
if(!_189){
doLoad(_185,http,url,_186,_190);
}
return;
};
dojo.io.transports.addTransport("XMLHTTPTransport");
};
dojo.require("dojo.alg.*");
dojo.provide("dojo.event.Event");
dojo.event=new function(){
var _194=0;
this.anon={};
this.nameAnonFunc=function(_195,_196){
var nso=(_196||this.anon);
if((dj_global["djConfig"])&&(djConfig["slowAnonFuncLookups"]==true)){
for(var x in nso){
if(nso[x]===_195){
dj_debug(x);
return x;
}
}
}
var ret="_"+_194++;
while(typeof nso[ret]!="undefined"){
ret="_"+_194++;
}
nso[ret]=_195;
return ret;
};
this.createFunctionPair=function(obj,cb){
var ret=[];
if(typeof obj=="function"){
ret[1]=dojo.event.nameAnonFunc(obj,dj_global);
ret[0]=dj_global;
return ret;
}else{
if((typeof obj=="object")&&(typeof cb=="string")){
return [obj,cb];
}else{
if((typeof obj=="object")&&(typeof cb=="function")){
ret[1]=dojo.event.nameAnonFunc(cb,obj);
ret[0]=obj;
return ret;
}
}
}
return null;
};
this.matchSignature=function(args,_198){
var end=Math.min(args.length,_198.length);
for(var x=0;x<end;x++){
if(compareTypes){
if((typeof args[x]).toLowerCase()!=(typeof _198[x])){
return false;
}
}else{
if((typeof args[x]).toLowerCase()!=_198[x].toLowerCase()){
return false;
}
}
}
return true;
};
this.matchSignatureSets=function(args){
for(var x=1;x<arguments.length;x++){
if(this.matchSignature(args,arguments[x])){
return true;
}
}
return false;
};
function interpolateArgs(args){
var ao={srcObj:dj_global,srcFunc:null,adviceObj:dj_global,adviceFunc:null,aroundObj:null,aroundFunc:null,adviceType:(args.length>2)?args[0]:"after",precedence:"last",once:false,delay:null};
switch(args.length){
case 0:
return;
case 1:
return;
case 2:
ao.srcFunc=args[0];
ao.adviceFunc=args[1];
break;
case 3:
if((typeof args[0]=="object")&&(typeof args[1]=="string")&&(typeof args[2]=="string")){
ao.adviceType="after";
ao.srcObj=args[0];
ao.srcFunc=args[1];
ao.adviceFunc=args[2];
}else{
if((typeof args[1]=="string")&&(typeof args[2]=="string")){
ao.srcFunc=args[1];
ao.adviceFunc=args[2];
}else{
if((typeof args[0]=="object")&&(typeof args[1]=="string")&&(typeof args[2]=="function")){
ao.adviceType="after";
ao.srcObj=args[0];
ao.srcFunc=args[1];
var _201=dojo.event.nameAnonFunc(args[2],ao.adviceObj);
ao.adviceObj[_201]=args[2];
ao.adviceFunc=_201;
}else{
if((typeof args[0]=="function")&&(typeof args[1]=="object")&&(typeof args[2]=="string")){
ao.adviceType="after";
ao.srcObj=dj_global;
var _201=dojo.event.nameAnonFunc(args[0],ao.srcObj);
ao.srcObj[_201]=args[0];
ao.srcFunc=_201;
ao.adviceObj=args[1];
ao.adviceFunc=args[2];
}
}
}
}
break;
case 4:
if((typeof args[0]=="object")&&(typeof args[2]=="object")){
ao.adviceType="after";
ao.srcObj=args[0];
ao.srcFunc=args[1];
ao.adviceObj=args[2];
ao.adviceFunc=args[3];
}else{
if((typeof args[1]).toLowerCase()=="object"){
ao.srcObj=args[1];
ao.srcFunc=args[2];
ao.adviceObj=dj_global;
ao.adviceFunc=args[3];
}else{
if((typeof args[2]).toLowerCase()=="object"){
ao.srcObj=dj_global;
ao.srcFunc=args[1];
ao.adviceObj=args[2];
ao.adviceFunc=args[3];
}else{
ao.srcObj=ao.adviceObj=ao.aroundObj=dj_global;
ao.srcFunc=args[1];
ao.adviceFunc=args[2];
ao.aroundFunc=args[3];
}
}
}
break;
case 6:
ao.srcObj=args[1];
ao.srcFunc=args[2];
ao.adviceObj=args[3];
ao.adviceFunc=args[4];
ao.aroundFunc=args[5];
ao.aroundObj=dj_global;
break;
default:
ao.srcObj=args[1];
ao.srcFunc=args[2];
ao.adviceObj=args[3];
ao.adviceFunc=args[4];
ao.aroundObj=args[5];
ao.aroundFunc=args[6];
ao.once=args[7];
ao.delay=args[8];
break;
}
if((typeof ao.srcFunc).toLowerCase()!="string"){
ao.srcFunc=dojo.alg.getNameInObj(ao.srcObj,ao.srcFunc);
}
if((typeof ao.adviceFunc).toLowerCase()!="string"){
ao.adviceFunc=dojo.alg.getNameInObj(ao.adviceObj,ao.adviceFunc);
}
if((ao.aroundObj)&&((typeof ao.aroundFunc).toLowerCase()!="string")){
ao.aroundFunc=dojo.alg.getNameInObj(ao.aroundObj,ao.aroundFunc);
}
if(!ao.srcObj){
dj_throw("bad srcObj for srcFunc: "+ao.srcFunc);
}
if(!ao.adviceObj){
dj_throw("bad srcObj for srcFunc: "+ao.adviceFunc);
}
return ao;
}
this.connect=function(){
var ao=interpolateArgs(arguments);
var mjp=dojo.event.MethodJoinPoint.getForMethod(ao.srcObj,ao.srcFunc);
if(ao.adviceFunc){
var mjp2=dojo.event.MethodJoinPoint.getForMethod(ao.adviceObj,ao.adviceFunc);
}
mjp.kwAddAdvice(ao);
return mjp;
};
this.connectBefore=function(){
var args=["before"];
for(var i=0;i<arguments.length;i++){
args.push(arguments[i]);
}
return this.connect.apply(this,args);
};
this.connectAround=function(){
var args=["around"];
for(var i=0;i<arguments.length;i++){
args.push(arguments[i]);
}
return this.connect.apply(this,args);
};
this.kwConnectImpl_=function(_204,_205){
var fn=(_205)?"disconnect":"connect";
if(typeof _204["srcFunc"]=="function"){
_204.srcObj=_204["srcObj"]||dj_global;
var _206=dojo.event.nameAnonFunc(_204.srcFunc,_204.srcObj);
_204.srcFunc=_206;
}
if(typeof _204["adviceFunc"]=="function"){
_204.adviceObj=_204["adviceObj"]||dj_global;
var _206=dojo.event.nameAnonFunc(_204.adviceFunc,_204.adviceObj);
_204.adviceFunc=_206;
}
return dojo.event[fn]((_204["type"]||_204["adviceType"]||"after"),_204["srcObj"],_204["srcFunc"],_204["adviceObj"]||_204["targetObj"],_204["adviceFunc"]||_204["targetFunc"],_204["aroundObj"],_204["aroundFunc"],_204["once"],_204["delay"]);
};
this.kwConnect=function(_207){
return this.kwConnectImpl_(_207,false);
};
this.disconnect=function(){
var ao=interpolateArgs(arguments);
if(!ao.adviceFunc){
return;
}
var mjp=dojo.event.MethodJoinPoint.getForMethod(ao.srcObj,ao.srcFunc);
return mjp.removeAdvice(ao.adviceObj,ao.adviceFunc,ao.adviceType,ao.once);
};
this.kwDisconnect=function(_208){
return this.kwConnectImpl_(_208,true);
};
};
dojo.event.MethodInvocation=function(_209,obj,args){
this.jp_=_209;
this.object=obj;
this.args=[];
for(var x=0;x<args.length;x++){
this.args[x]=args[x];
}
this.around_index=-1;
};
dojo.event.MethodInvocation.prototype.proceed=function(){
this.around_index++;
if(this.around_index>=this.jp_.around.length){
return this.jp_.object[this.jp_.methodname].apply(this.jp_.object,this.args);
}else{
var ti=this.jp_.around[this.around_index];
var mobj=ti[0]||dj_global;
var meth=ti[1];
return mobj[meth].call(mobj,this);
}
};
dojo.event.MethodJoinPoint=function(obj,_212){
this.object=obj||dj_global;
this.methodname=_212;
this.methodfunc=this.object[_212];
this.before=[];
this.after=[];
this.around=[];
};
dojo.event.MethodJoinPoint.getForMethod=function(obj,_213){
if(!obj){
obj=dj_global;
}
if(!obj[_213]){
obj[_213]=function(){
};
}else{
if(typeof obj[_213]!="function"){
return null;
}
}
var _214=_213+"$joinpoint";
var _215=_213+"$joinpoint$method";
var _216=obj[_214];
if(!_216){
var _217=false;
if(dojo.event["browser"]){
if((obj["attachEvent"])||(obj["nodeType"])||(obj["addEventListener"])){
_217=true;
dojo.event.browser.addClobberAttrs(_214,_215,_213);
dojo.event.browser.addClobberNode(obj);
}
}
obj[_215]=obj[_213];
_216=obj[_214]=new dojo.event.MethodJoinPoint(obj,_215);
obj[_213]=function(){
var args=[];
if((_217)&&(!arguments.length)&&(window.event)){
args.push(dojo.event.browser.fixEvent(window.event));
}else{
for(var x=0;x<arguments.length;x++){
if((x==0)&&(_217)&&(typeof Event!="undefined")&&(arguments[x] instanceof Event)){
args.push(dojo.event.browser.fixEvent(arguments[x]));
}else{
args.push(arguments[x]);
}
}
}
return _216.run.apply(_216,args);
};
}
return _216;
};
dojo.event.MethodJoinPoint.prototype.unintercept=function(){
this.object[this.methodname]=this.methodfunc;
};
dojo.event.MethodJoinPoint.prototype.run=function(){
var obj=this.object||dj_global;
var args=arguments;
var _218=[];
for(var x=0;x<args.length;x++){
_218[x]=args[x];
}
var _219=function(marr){
var _221=marr[0]||dj_global;
var _222=marr[1];
if(!_221[_222]){
throw new Error("function \""+_222+"\" does not exist on \""+_221+"\"");
}
var _223=marr[2]||dj_global;
var _224=marr[3];
var _225;
var _226=parseInt(marr[4]);
var _227=((!isNaN(_226))&&(marr[4]!==null)&&(typeof marr[4]!="undefined"));
var to={args:[],jp_:this,object:obj,proceed:function(){
return _221[_222].apply(_221,to.args);
}};
to.args=_218;
if(_224){
_223[_224].call(_223,to);
}else{
if((_227)&&((dojo.render.html)||(dojo.render.svg))){
dj_global["setTimeout"](function(){
_221[_222].apply(_221,args);
},_226);
}else{
_221[_222].apply(_221,args);
}
}
};
if(this.before.length>0){
dojo.alg.forEach(this.before,_219,true);
}
var _229;
if(this.around.length>0){
var mi=new dojo.event.MethodInvocation(this,obj,args);
_229=mi.proceed();
}else{
if(this.methodfunc){
_229=this.object[this.methodname].apply(this.object,args);
}
}
if(this.after.length>0){
dojo.alg.forEach(this.after,_219,true);
}
return (this.methodfunc)?_229:null;
};
dojo.event.MethodJoinPoint.prototype.getArr=function(kind){
var arr=this.after;
if((typeof kind=="string")&&(kind.indexOf("before")!=-1)){
arr=this.before;
}else{
if(kind=="around"){
arr=this.around;
}
}
return arr;
};
dojo.event.MethodJoinPoint.prototype.kwAddAdvice=function(args){
this.addAdvice(args["adviceObj"],args["adviceFunc"],args["aroundObj"],args["aroundFunc"],args["adviceType"],args["precedence"],args["once"],args["delay"]);
};
dojo.event.MethodJoinPoint.prototype.addAdvice=function(_232,_233,_234,_235,_236,_237,once,_239){
var arr=this.getArr(_236);
if(!arr){
dj_throw("bad this: "+this);
}
var ao=[_232,_233,_234,_235,_239];
if(once){
if(this.hasAdvice(_232,_233,_236,arr)>=0){
return;
}
}
if(_237=="first"){
arr.unshift(ao);
}else{
arr.push(ao);
}
};
dojo.event.MethodJoinPoint.prototype.hasAdvice=function(_240,_241,_242,arr){
if(!arr){
arr=this.getArr(_242);
}
var ind=-1;
for(var x=0;x<arr.length;x++){
if((arr[x][0]==_240)&&(arr[x][1]==_241)){
ind=x;
}
}
return ind;
};
dojo.event.MethodJoinPoint.prototype.removeAdvice=function(_244,_245,_246,once){
var arr=this.getArr(_246);
var ind=this.hasAdvice(_244,_245,_246,arr);
if(ind==-1){
return false;
}
while(ind!=-1){
arr.splice(ind,1);
if(once){
break;
}
ind=this.hasAdvice(_244,_245,_246,arr);
}
return true;
};
dojo.provide("dojo.event.Event");
dojo.provide("dojo.event.Topic");
dojo.require("dojo.event.Event");
dojo.event.Topic={};
dojo.event.topic=new function(){
this.topics={};
this.getTopic=function(_247){
if(!this.topics[_247]){
this.topics[_247]=new this.TopicImpl(_247);
}
return this.topics[_247];
};
this.registerPublisher=function(_248,obj,_249){
var _248=this.getTopic(_248);
_248.registerPublisher(obj,_249);
};
this.subscribe=function(_250,obj,_251){
var _250=this.getTopic(_250);
_250.subscribe(obj,_251);
};
this.unsubscribe=function(_252,obj,_253){
var _252=this.getTopic(_252);
_252.subscribe(obj,_253);
};
this.publish=function(_254,_255){
var _254=this.getTopic(_254);
var args=[];
if((arguments.length==2)&&(_255.length)&&(typeof _255!="string")){
args=_255;
}else{
var args=[];
for(var x=1;x<arguments.length;x++){
args.push(arguments[x]);
}
}
_254.sendMessage.apply(_254,args);
};
};
dojo.event.topic.TopicImpl=function(_256){
this.topicName=_256;
var self=this;
self.subscribe=function(_258,_259){
dojo.event.connect("before",self,"sendMessage",_258,_259);
};
self.unsubscribe=function(_260,_261){
dojo.event.disconnect("before",self,"sendMessage",_260,_261);
};
self.registerPublisher=function(_262,_263){
dojo.event.connect(_262,_263,self,"sendMessage");
};
self.sendMessage=function(_264){
};
};
dojo.provide("dojo.event.BrowserEvent");
dojo.event.browser={};
dojo.require("dojo.event.Event");
dojo_ie_clobber=new function(){
this.clobberArr=["data","onload","onmousedown","onmouseup","onmouseover","onmouseout","onmousemove","onclick","ondblclick","onfocus","onblur","onkeypress","onkeydown","onkeyup","onsubmit","onreset","onselect","onchange","onselectstart","ondragstart","oncontextmenu"];
this.exclusions=[];
this.clobberList={};
this.clobberNodes=[];
this.addClobberAttr=function(type){
if(dojo.render.html.ie){
if(this.clobberList[type]!="set"){
this.clobberArr.push(type);
this.clobberList[type]="set";
}
}
};
this.addExclusionID=function(id){
this.exclusions.push(id);
};
if(dojo.render.html.ie){
for(var x=0;x<this.clobberArr.length;x++){
this.clobberList[this.clobberArr[x]]="set";
}
}
this.clobber=function(_266){
for(var x=0;x<this.exclusions.length;x++){
try{
var tn=document.getElementById(this.exclusions[x]);
tn.parentNode.removeChild(tn);
}
catch(e){
}
}
var na;
if(_266){
var tna=_266.getElementsByTagName("*");
na=[_266];
for(var x=0;x<tna.length;x++){
na.push(tna[x]);
}
}else{
na=(this.clobberNodes.length)?this.clobberNodes:document.all;
}
for(var i=na.length-1;i>=0;i=i-1){
var el=na[i];
for(var p=this.clobberArr.length-1;p>=0;p=p-1){
var ta=this.clobberArr[p];
try{
el[ta]=null;
el.removeAttribute(ta);
delete el[ta];
}
catch(e){
}
}
}
};
};
if((dojo.render.html.ie)&&((!dojo.hostenv.ie_prevent_clobber_)||(dojo.hostenv.ie_clobber_minimal_))){
window.onunload=function(){
dojo_ie_clobber.clobber();
if((dojo["widget"])&&(dojo.widget["manager"])){
dojo.widget.manager.destroyAll();
}
CollectGarbage();
};
}
dojo.event.browser=new function(){
this.clean=function(node){
if(dojo.render.html.ie){
dojo_ie_clobber.clobber(node);
}
};
this.addClobberAttr=function(type){
dojo_ie_clobber.addClobberAttr(type);
};
this.addClobberAttrs=function(){
for(var x=0;x<arguments.length;x++){
this.addClobberAttr(arguments[x]);
}
};
this.addClobberNode=function(node){
if(dojo.hostenv.ie_clobber_minimal_){
if(!node.__doClobber__){
dojo_ie_clobber.clobberNodes.push(node);
node.__doClobber__=true;
}
}
};
this.addListener=function(node,_272,fp,_273){
if(!_273){
var _273=false;
}
_272=_272.toLowerCase();
if(_272.substr(0,2)=="on"){
_272=_272.substr(2);
}
if(!node){
return;
}
var _274=function(evt){
if(!evt){
evt=window.event;
}
var ret=fp(dojo.event.browser.fixEvent(evt));
if(_273){
dojo.event.browser.stopEvent(evt);
}
return ret;
};
var _275="on"+_272;
if(node.addEventListener){
node.addEventListener(_272,_274,_273);
return true;
}else{
if(typeof node[_275]=="function"){
var _276=node[_275];
node[_275]=function(e){
_276(e);
_274(e);
};
}else{
node[_275]=_274;
}
if(dojo.render.html.ie){
this.addClobberAttr(_275);
this.addClobberNode(node);
}
return true;
}
};
this.fixEvent=function(evt){
if(evt.type&&evt.type.indexOf("key")==0){
var keys={KEY_BACKSPACE:8,KEY_TAB:9,KEY_ENTER:13,KEY_SHIFT:16,KEY_CTRL:17,KEY_ALT:18,KEY_PAUSE:19,KEY_CAPS_LOCK:20,KEY_ESCAPE:27,KEY_PAGE_UP:33,KEY_PAGE_DOWN:34,KEY_END:35,KEY_HOME:36,KEY_LEFT_ARROW:37,KEY_UP_ARROW:38,KEY_RIGHT_ARROW:39,KEY_DOWN_ARROW:40,KEY_INSERT:45,KEY_DELETE:46,KEY_LEFT_WINDOW:91,KEY_RIGHT_WINDOW:92,KEY_SELECT:93,KEY_F1:112,KEY_F2:113,KEY_F3:114,KEY_F4:115,KEY_F5:116,KEY_F6:117,KEY_F7:118,KEY_F8:119,KEY_F9:120,KEY_F10:121,KEY_F11:122,KEY_F12:123,KEY_NUM_LOCK:144,KEY_SCROLL_LOCK:145};
evt.keys=[];
for(var key in keys){
evt[key]=keys[key];
evt.keys[keys[key]]=key;
}
if(dojo.render.html.ie&&evt.type=="keypress"){
evt.charCode=evt.keyCode;
}
}
if(dojo.render.html.ie){
if(!evt.target){
evt.target=evt.srcElement;
}
if(!evt.currentTarget){
evt.currentTarget=evt.srcElement;
}
if(!evt.layerX){
evt.layerX=evt.offsetX;
}
if(!evt.layerY){
evt.layerY=evt.offsetY;
}
if(evt.fromElement){
evt.relatedTarget=evt.fromElement;
}
if(evt.toElement){
evt.relatedTarget=evt.toElement;
}
evt.callListener=function(_280,_281){
if(typeof _280!="function"){
dj_throw("listener not a function: "+_280);
}
evt.currentTarget=_281;
var ret=_280.call(_281,evt);
return ret;
};
evt.stopPropagation=function(){
evt.cancelBubble=true;
};
evt.preventDefault=function(){
evt.returnValue=false;
};
}
return evt;
};
this.stopEvent=function(ev){
if(window.event){
ev.returnValue=false;
ev.cancelBubble=true;
}else{
ev.preventDefault();
ev.stopPropagation();
}
};
};
dojo.hostenv.conditionalLoadModule({common:["dojo.event.Event","dojo.event.Topic"],browser:["dojo.event.BrowserEvent"]});
dojo.hostenv.moduleLoaded("dojo.event.*");
dojo.provide("dojo.math");
dojo.math=new function(){
this.degToRad=function(x){
return (x*Math.PI)/180;
};
this.radToDeg=function(x){
return (x*180)/Math.PI;
};
this.factorial=function(n){
if(n<1){
return 0;
}
var _284=1;
for(var i=1;i<=n;i++){
_284*=i;
}
return _284;
};
this.permutations=function(n,k){
if(n==0||k==0){
return 1;
}
return (this.factorial(n)/this.factorial(n-k));
};
this.combinations=function(n,r){
if(n==0||r==0){
return 1;
}
return (this.factorial(n)/(this.factorial(n-r)*this.factorial(r)));
};
this.bernstein=function(t,n,i){
return (this.combinations(n,i)*Math.pow(t,i)*Math.pow(1-t,n-i));
};
};
dojo.provide("dojo.math.Math");
dojo.provide("dojo.math.curves");
dojo.require("dojo.math.Math");
dojo.math.curves={Line:function(_287,end){
this.start=_287;
this.end=end;
this.dimensions=_287.length;
for(var i=0;i<_287.length;i++){
_287[i]=Number(_287[i]);
}
for(var i=0;i<end.length;i++){
end[i]=Number(end[i]);
}
this.getValue=function(n){
var _288=new Array(this.dimensions);
for(var i=0;i<this.dimensions;i++){
_288[i]=((this.end[i]-this.start[i])*n)+this.start[i];
}
return _288;
};
return this;
},Bezier:function(pnts){
this.getValue=function(step){
if(step>=1){
step=0.99999999;
}
var _291=new Array(this.p[0].length);
for(var k=0;j<this.p[0].length;k++){
_291[k]=0;
}
for(var j=0;j<this.p[0].length;j++){
var C=0;
var D=0;
for(var i=0;i<this.p.length;i++){
C+=this.p[i][j]*this.p[this.p.length-1][0]*dojo.math.bernstein(step,this.p.length,i);
}
for(var l=0;l<this.p.length;l++){
D+=this.p[this.p.length-1][0]*dojo.math.bernstein(step,this.p.length,l);
}
_291[j]=C/D;
}
return _291;
};
this.p=pnts;
return this;
},CatmullRom:function(pnts,c){
this.getValue=function(step){
var _296=step*(this.p.length-1);
var node=Math.floor(_296);
var _297=_296-node;
var i0=node-1;
if(i0<0){
i0=0;
}
var i=node;
var i1=node+1;
if(i1>=this.p.length){
i1=this.p.length-1;
}
var i2=node+2;
if(i2>=this.p.length){
i2=this.p.length-1;
}
var u=_297;
var u2=_297*_297;
var u3=_297*_297*_297;
var _304=new Array(this.p[0].length);
for(var k=0;k<this.p[0].length;k++){
var x1=(-this.c*this.p[i0][k])+((2-this.c)*this.p[i][k])+((this.c-2)*this.p[i1][k])+(this.c*this.p[i2][k]);
var x2=(2*this.c*this.p[i0][k])+((this.c-3)*this.p[i][k])+((3-2*this.c)*this.p[i1][k])+(-this.c*this.p[i2][k]);
var x3=(-this.c*this.p[i0][k])+(this.c*this.p[i1][k]);
var x4=this.p[i][k];
_304[k]=x1*u3+x2*u2+x3*u+x4;
}
return _304;
};
if(!c){
this.c=0.7;
}else{
this.c=c;
}
this.p=pnts;
return this;
},Arc:function(_309,end,ccw){
var _311=dojo.math.points.midpoint(_309,end);
var _312=dojo.math.points.translate(dojo.math.points.invert(_311),_309);
var rad=Math.sqrt(Math.pow(_312[0],2)+Math.pow(_312[1],2));
var _314=dojo.math.radToDeg(Math.atan(_312[1]/_312[0]));
if(_312[0]<0){
_314-=90;
}else{
_314+=90;
}
dojo.math.curves.CenteredArc.call(this,_311,rad,_314,_314+(ccw?-180:180));
},CenteredArc:function(_315,_316,_317,end){
this.center=_315;
this.radius=_316;
this.start=_317||0;
this.end=end;
this.getValue=function(n){
var _318=new Array(2);
var _319=dojo.math.degToRad(this.start+((this.end-this.start)*n));
_318[0]=this.center[0]+this.radius*Math.sin(_319);
_318[1]=this.center[1]-this.radius*Math.cos(_319);
return _318;
};
return this;
},Circle:function(_320,_321){
dojo.math.curves.CenteredArc.call(this,_320,_321,0,360);
return this;
},Path:function(){
var _322=[];
var _323=[];
var _324=[];
var _325=0;
this.add=function(_326,_327){
if(_327<0){
dj_throw("dojo.math.curves.Path.add: weight cannot be less than 0");
}
_322.push(_326);
_323.push(_327);
_325+=_327;
computeRanges();
};
this.remove=function(_328){
for(var i=0;i<_322.length;i++){
if(_322[i]==_328){
_322.splice(i,1);
_325-=_323.splice(i,1)[0];
break;
}
}
computeRanges();
};
this.removeAll=function(){
_322=[];
_323=[];
_325=0;
};
this.getValue=function(n){
var _329=false,value=0;
for(var i=0;i<_324.length;i++){
var r=_324[i];
if(n>=r[0]&&n<r[1]){
var subN=(n-r[0])/r[2];
value=_322[i].getValue(subN);
_329=true;
break;
}
}
if(!_329){
value=_322[_322.length-1].getValue(1);
}
for(j=0;j<i;j++){
value=dojo.math.points.translate(value,_322[j].getValue(1));
}
return value;
};
function computeRanges(){
var _331=0;
for(var i=0;i<_323.length;i++){
var end=_331+_323[i]/_325;
var len=end-_331;
_324[i]=[_331,end,len];
_331=end;
}
}
return this;
}};
dojo.provide("dojo.animation");
dojo.provide("dojo.animation.Animation");
dojo.require("dojo.math.Math");
dojo.require("dojo.math.curves");
dojo.animation={};
dojo.animation.Animation=function(_333,_334,_335,_336){
var _337=this;
this.curve=_333;
this.duration=_334;
this.accel=_335;
this.repeatCount=_336||0;
this.animSequence_=null;
this.onBegin=null;
this.onAnimate=null;
this.onEnd=null;
this.onPlay=null;
this.onPause=null;
this.onStop=null;
this.handler=null;
var _338=null,endTime=null,lastFrame=null,timer=null,percent=0,active=false,paused=false;
this.play=function(_339){
if(_339){
clearTimeout(timer);
active=false;
paused=false;
percent=0;
}else{
if(active&&!paused){
return;
}
}
_338=new Date().valueOf();
if(paused){
_338-=(_337.duration*percent/100);
}
endTime=_338+_337.duration;
lastFrame=_338;
var e=new dojo.animation.AnimationEvent(_337,null,_337.curve.getValue(percent),_338,_338,endTime,_337.duration,percent,0);
active=true;
paused=false;
if(percent==0){
e.type="begin";
if(typeof _337.handler=="function"){
_337.handler(e);
}
if(typeof _337.onBegin=="function"){
_337.onBegin(e);
}
}
e.type="play";
if(typeof _337.handler=="function"){
_337.handler(e);
}
if(typeof _337.onPlay=="function"){
_337.onPlay(e);
}
if(this.animSequence_){
this.animSequence_.setCurrent(this);
}
cycle();
};
this.pause=function(){
clearTimeout(timer);
if(!active){
return;
}
paused=true;
var e=new dojo.animation.AnimationEvent(_337,"pause",_337.curve.getValue(percent),_338,new Date().valueOf(),endTime,_337.duration,percent,0);
if(typeof _337.handler=="function"){
_337.handler(e);
}
if(typeof _337.onPause=="function"){
_337.onPause(e);
}
};
this.playPause=function(){
if(!active||paused){
_337.play();
}else{
_337.pause();
}
};
this.gotoPercent=function(pct,_341){
clearTimeout(timer);
active=true;
paused=true;
percent=pct;
if(_341){
this.play();
}
};
this.stop=function(_342){
clearTimeout(timer);
var step=percent/100;
if(_342){
step=1;
}
var e=new dojo.animation.AnimationEvent(_337,"stop",_337.curve.getValue(step),_338,new Date().valueOf(),endTime,_337.duration,percent,Math.round(fps));
if(typeof _337.handler=="function"){
_337.handler(e);
}
if(typeof _337.onStop=="function"){
_337.onStop(e);
}
active=false;
paused=false;
};
this.status=function(){
if(active){
return paused?"paused":"playing";
}else{
return "stopped";
}
};
function cycle(){
clearTimeout(timer);
if(active){
var curr=new Date().valueOf();
var step=(curr-_338)/(endTime-_338);
fps=1000/(curr-lastFrame);
lastFrame=curr;
if(step>=1){
step=1;
percent=100;
}else{
percent=step*100;
}
var e=new dojo.animation.AnimationEvent(_337,"animate",_337.curve.getValue(step),_338,curr,endTime,_337.duration,percent,Math.round(fps));
if(typeof _337.handler=="function"){
_337.handler(e);
}
if(typeof _337.onAnimate=="function"){
_337.onAnimate(e);
}
if(step<1){
timer=setTimeout(cycle,10);
}else{
e.type="end";
active=false;
if(typeof _337.handler=="function"){
_337.handler(e);
}
if(typeof _337.onEnd=="function"){
_337.onEnd(e);
}
if(_337.repeatCount>0){
_337.repeatCount--;
_337.play(true);
}else{
if(_337.repeatCount==-1){
_337.play(true);
}else{
if(_337.animSequence_){
_337.animSequence_.playNext();
}
}
}
}
}
}
};
dojo.animation.AnimationEvent=function(anim,type,_345,_346,_347,_348,dur,pct,fps){
this.type=type;
this.animation=anim;
this.coords=_345;
this.x=_345[0];
this.y=_345[1];
this.z=_345[2];
this.startTime=_346;
this.currentTime=_347;
this.endTime=_348;
this.duration=dur;
this.percent=pct;
this.fps=fps;
this.coordsAsInts=function(){
var _351=new Array(this.coords.length);
for(var i=0;i<this.coords.length;i++){
_351[i]=Math.round(this.coords[i]);
}
return _351;
};
return this;
};
dojo.animation.AnimationSequence=function(_352){
var _353=[];
var _354=-1;
this.repeatCount=_352||0;
this.onBegin=null;
this.onEnd=null;
this.onNext=null;
this.handler=null;
this.add=function(){
for(var i=0;i<arguments.length;i++){
_353.push(arguments[i]);
arguments[i].animSequence_=this;
}
};
this.remove=function(anim){
for(var i=0;i<_353.length;i++){
if(_353[i]==anim){
_353[i].animSequence_=null;
_353.splice(i,1);
break;
}
}
};
this.removeAll=function(){
for(var i=0;i<_353.length;i++){
_353[i].animSequence_=null;
}
_353=[];
_354=-1;
};
this.play=function(_355){
if(_353.length==0){
return;
}
if(_355||!_353[_354]){
_354=0;
}
if(_353[_354]){
if(_354==0){
var e={type:"begin",animation:_353[_354]};
if(typeof this.handler=="function"){
this.handler(e);
}
if(typeof this.onBegin=="function"){
this.onBegin(e);
}
}
_353[_354].play(_355);
}
};
this.pause=function(){
if(_353[_354]){
_353[_354].pause();
}
};
this.playPause=function(){
if(_353.length==0){
return;
}
if(_354==-1){
_354=0;
}
if(_353[_354]){
_353[_354].playPause();
}
};
this.stop=function(){
if(_353[_354]){
_353[_354].stop();
}
};
this.status=function(){
if(_353[_354]){
return _353[_354].status();
}else{
return "stopped";
}
};
this.setCurrent=function(anim){
for(var i=0;i<_353.length;i++){
if(_353[i]==anim){
_354=i;
break;
}
}
};
this.playNext=function(){
if(_354==-1||_353.length==0){
return;
}
_354++;
if(_353[_354]){
var e={type:"next",animation:_353[_354]};
if(typeof this.handler=="function"){
this.handler(e);
}
if(typeof this.onNext=="function"){
this.onNext(e);
}
_353[_354].play(true);
}else{
var e={type:"end",animation:_353[_353.length-1]};
if(typeof this.handler=="function"){
this.handler(e);
}
if(typeof this.onEnd=="function"){
this.onEnd(e);
}
if(this.repeatCount>0){
_354=0;
this.repeatCount--;
_353[_354].play(true);
}else{
if(this.repeatCount==-1){
_354=0;
_353[_354].play(true);
}else{
_354=-1;
}
}
}
};
};
dojo.hostenv.conditionalLoadModule({common:["dojo.animation.Animation",false,false]});
dojo.hostenv.moduleLoaded("dojo.animation.*");
dojo.provide("dojo.graphics.color");
dojo.graphics.color=new function(){
this.blend=function(a,b,_357){
if(typeof a=="string"){
return this.blendHex(a,b,_357);
}
if(!_357){
_357=0;
}else{
if(_357>1){
_357=1;
}else{
if(_357<-1){
_357=-1;
}
}
}
var c=new Array(3);
for(var i=0;i<3;i++){
var half=Math.abs(a[i]-b[i])/2;
c[i]=Math.floor(Math.min(a[i],b[i])+half+(half*_357));
}
return c;
};
this.blendHex=function(a,b,_359){
return this.rgb2hex(this.blend(this.hex2rgb(a),this.hex2rgb(b),_359));
};
this.extractRGB=function(_360){
var hex="0123456789abcdef";
_360=_360.toLowerCase();
if(_360.indexOf("rgb")==0){
var _362=_360.match(/rgba*\((\d+), *(\d+), *(\d+)/i);
var ret=_362.splice(1,3);
return ret;
}else{
if(_360.indexOf("#")==0){
var _363=[];
_360=_360.substring(1);
if(_360.length==3){
_363[0]=_360.charAt(0)+_360.charAt(0);
_363[1]=_360.charAt(1)+_360.charAt(1);
_363[2]=_360.charAt(2)+_360.charAt(2);
}else{
_363[0]=_360.substring(0,2);
_363[1]=_360.substring(2,4);
_363[2]=_360.substring(4,6);
}
for(var i=0;i<_363.length;i++){
var c=_363[i];
_363[i]=hex.indexOf(c.charAt(0))*16+hex.indexOf(c.charAt(1));
}
return _363;
}else{
switch(_360){
case "white":
return [255,255,255];
case "black":
return [0,0,0];
case "red":
return [255,0,0];
case "green":
return [0,255,0];
case "blue":
return [0,0,255];
case "navy":
return [0,0,128];
case "gray":
return [128,128,128];
case "silver":
return [192,192,192];
}
}
}
return [255,255,255];
};
this.hex2rgb=function(hex){
var _364="0123456789ABCDEF";
var rgb=new Array(3);
if(hex.indexOf("#")==0){
hex=hex.substring(1);
}
hex=hex.toUpperCase();
if(hex.length==3){
rgb[0]=hex.charAt(0)+hex.charAt(0);
rgb[1]=hex.charAt(1)+hex.charAt(1);
rgb[2]=hex.charAt(2)+hex.charAt(2);
}else{
rgb[0]=hex.substring(0,2);
rgb[1]=hex.substring(2,4);
rgb[2]=hex.substring(4);
}
for(var i=0;i<rgb.length;i++){
rgb[i]=_364.indexOf(rgb[i].charAt(0))*16+_364.indexOf(rgb[i].charAt(1));
}
return rgb;
};
this.rgb2hex=function(r,g,b){
if(r.constructor==Array){
g=r[1]||0;
b=r[2]||0;
r=r[0]||0;
}
return ["#",r.toString(16),g.toString(16),b.toString(16)].join("");
};
};
dojo.provide("dojo.text.String");
dojo.text={trim:function(_367){
if(arguments.length==0){
_367=this;
}
if(typeof _367!="string"){
return _367;
}
if(!_367.length){
return _367;
}
return _367.replace(/^\s*/,"").replace(/\s*$/,"");
},paramString:function(str,_369,_370){
if(typeof str!="string"){
_369=str;
_370=_369;
str=this;
}
for(var name in _369){
var re=new RegExp("\\%\\{"+name+"\\}","g");
str=str.replace(re,_369[name]);
}
if(_370){
str=str.replace(/%\{([^\}\s]+)\}/g,"");
}
return str;
},capitalize:function(str){
if(typeof str!="string"||str==null){
return "";
}
if(arguments.length==0){
str=this;
}
var _372=str.split(" ");
var _373="";
var len=_372.length;
for(var i=0;i<len;i++){
var word=_372[i];
word=word.charAt(0).toUpperCase()+word.substring(1,word.length);
_373+=word;
if(i<len-1){
_373+=" ";
}
}
return new String(_373);
},isBlank:function(str){
if(typeof str!="string"||str==null){
return true;
}
return (dojo.text.trim(str).length==0);
}};
dojo.text.String={};
dojo.provide("dojo.xml.domUtil");
dojo.require("dojo.graphics.color");
dojo.require("dojo.text.String");
dojo.xml.domUtil=new function(){
this.nodeTypes={ELEMENT_NODE:1,ATTRIBUTE_NODE:2,TEXT_NODE:3,CDATA_SECTION_NODE:4,ENTITY_REFERENCE_NODE:5,ENTITY_NODE:6,PROCESSING_INSTRUCTION_NODE:7,COMMENT_NODE:8,DOCUMENT_NODE:9,DOCUMENT_TYPE_NODE:10,DOCUMENT_FRAGMENT_NODE:11,NOTATION_NODE:12};
this.dojoml="http://www.dojotoolkit.org/2004/dojoml";
this.idIncrement=0;
this.getTagName=function(node){
var _375=node.tagName;
if(_375.substr(0,5).toLowerCase()!="dojo:"){
if(_375.substr(0,4).toLowerCase()=="dojo"){
return "dojo:"+_375.substring(4).toLowerCase();
}
var djt=node.getAttribute("dojoType")||node.getAttribute("dojotype");
if(djt){
return "dojo:"+djt.toLowerCase();
}
if((node.getAttributeNS)&&(node.getAttributeNS(this.dojoml,"type"))){
return "dojo:"+node.getAttributeNS(this.dojoml,"type").toLowerCase();
}
try{
djt=node.getAttribute("dojo:type");
}
catch(e){
}
if(djt){
return "dojo:"+djt.toLowerCase();
}
if((!dj_global["djConfig"])||(!djConfig["ignoreClassNames"])){
var _377=node.className||node.getAttribute("class");
if((_377)&&(_377.indexOf("dojo-")!=-1)){
var _378=_377.split(" ");
for(var x=0;x<_378.length;x++){
if((_378[x].length>5)&&(_378[x].indexOf("dojo-")>=0)){
return "dojo:"+_378[x].substr(5);
}
}
}
}
}
return _375.toLowerCase();
};
this.getUniqueId=function(){
var base="dj_unique_";
this.idIncrement++;
while(document.getElementById(base+this.idIncrement)){
this.idIncrement++;
}
return base+this.idIncrement;
};
this.getFirstChildTag=function(_380){
var node=_380.firstChild;
while(node&&node.nodeType!=1){
node=node.nextSibling;
}
return node;
};
this.getLastChildTag=function(_381){
if(!node){
return null;
}
var node=_381.lastChild;
while(node&&node.nodeType!=1){
node=node.previousSibling;
}
return node;
};
this.getNextSiblingTag=function(node){
if(!node){
return null;
}
do{
node=node.nextSibling;
}while(node&&node.nodeType!=1);
return node;
};
this.getPreviousSiblingTag=function(node){
if(!node){
return null;
}
do{
node=node.previousSibling;
}while(node&&node.nodeType!=1);
return node;
};
this.forEachChildTag=function(node,_382){
var _383=this.getFirstChildTag(node);
while(_383){
if(_382(_383)=="break"){
break;
}
_383=this.getNextSiblingTag(_383);
}
};
this.moveChildren=function(_384,_385,trim){
var _387=0;
if(trim){
while(_384.hasChildNodes()&&_384.firstChild.nodeType==3){
_384.removeChild(_384.firstChild);
}
while(_384.hasChildNodes()&&_384.lastChild.nodeType==3){
_384.removeChild(_384.lastChild);
}
}
while(_384.hasChildNodes()){
_385.appendChild(_384.firstChild);
_387++;
}
return _387;
};
this.copyChildren=function(_388,_389,trim){
var cp=_388.cloneNode(true);
return this.moveChildren(cp,_389,trim);
};
this.clearChildren=function(node){
var _391=0;
while(node.hasChildNodes()){
node.removeChild(node.firstChild);
_391++;
}
return _391;
};
this.replaceChildren=function(node,_392){
this.clearChildren(node);
node.appendChild(_392);
};
this.getStyle=function(_393,_394){
var _395=undefined,camelCased=dojo.xml.domUtil.toCamelCase(_394);
_395=_393.style[camelCased];
if(!_395){
if(document.defaultView){
_395=document.defaultView.getComputedStyle(_393,"").getPropertyValue(_394);
}else{
if(_393.currentStyle){
_395=_393.currentStyle[camelCased];
}else{
if(_393.style.getPropertyValue){
_395=_393.style.getPropertyValue(_394);
}
}
}
}
return _395;
};
this.toCamelCase=function(_396){
var arr=_396.split("-"),cc=arr[0];
for(var i=1;i<arr.length;i++){
cc+=arr[i].charAt(0).toUpperCase()+arr[i].substring(1);
}
return cc;
};
this.toSelectorCase=function(_397){
return _397.replace(/([A-Z])/g,"-$1").toLowerCase();
};
this.getAncestors=function(node){
var _398=[];
while(node){
_398.push(node);
node=node.parentNode;
}
return _398;
};
this.isChildOf=function(node,_399,_400){
if(_400&&node){
node=node.parentNode;
}
while(node){
if(node==_399){
return true;
}
node=node.parentNode;
}
return false;
};
this.createDocumentFromText=function(str,_401){
if(!_401){
_401="text/xml";
}
if(typeof DOMParser!="undefined"){
var _402=new DOMParser();
return _402.parseFromString(str,_401);
}else{
if(typeof ActiveXObject!="undefined"){
var _403=new ActiveXObject("Microsoft.XMLDOM");
if(_403){
_403.async=false;
_403.loadXML(str);
return _403;
}else{
dj_debug("toXml didn't work?");
}
}else{
if(document.createElement){
var tmp=document.createElement("xml");
tmp.innerHTML=str;
if(document.implementation&&document.implementation.createDocument){
var _404=document.implementation.createDocument("foo","",null);
for(var i=0;i<tmp.childNodes.length;i++){
_404.importNode(tmp.childNodes.item(i),true);
}
return _404;
}
return tmp.document&&tmp.document.firstChild?tmp.document.firstChild:tmp;
}
}
}
return null;
};
if(dojo.render.html.capable){
this.createNodesFromText=function(txt,wrap){
var tn=document.createElement("div");
tn.style.visibility="hidden";
document.body.appendChild(tn);
tn.innerHTML=txt;
tn.normalize();
if(wrap){
var ret=[];
var fc=tn.firstChild;
ret[0]=((fc.nodeValue==" ")||(fc.nodeValue=="\t"))?fc.nextSibling:fc;
document.body.removeChild(tn);
return ret;
}
var _408=[];
for(var x=0;x<tn.childNodes.length;x++){
_408.push(tn.childNodes[x].cloneNode(true));
}
tn.style.display="none";
document.body.removeChild(tn);
return _408;
};
}else{
if(dojo.render.svg.capable){
this.createNodesFromText=function(txt,wrap){
var _409=parseXML(txt,window.document);
_409.normalize();
if(wrap){
var ret=[_409.firstChild.cloneNode(true)];
return ret;
}
var _410=[];
for(var x=0;x<_409.childNodes.length;x++){
_410.push(_409.childNodes.item(x).cloneNode(true));
}
return _410;
};
}
}
this.extractRGB=function(){
return dojo.graphics.color.extractRGB.call(dojo.graphics.color,arguments);
};
this.hex2rgb=function(){
return dojo.graphics.color.hex2rgb.call(dojo.graphics.color,arguments);
};
this.rgb2hex=function(){
return dojo.graphics.color.rgb2hex.call(dojo.graphics.color,arguments);
};
this.insertBefore=function(node,ref){
var pn=ref.parentNode;
pn.insertBefore(node,ref);
};
this.before=this.insertBefore;
this.insertAfter=function(node,ref){
var pn=ref.parentNode;
if(ref==pn.lastChild){
pn.appendChild(node);
}else{
pn.insertBefore(node,ref.nextSibling);
}
};
this.after=this.insertAfter;
this.insert=function(node,ref,_413){
switch(_413.toLowerCase()){
case "before":
this.before(node,ref);
break;
case "after":
this.after(node,ref);
break;
case "first":
if(ref.firstChild){
this.before(node,ref.firstChild);
}else{
ref.appendChild(node);
}
break;
default:
ref.appendChild(node);
break;
}
};
this.insertAtIndex=function(node,ref,_414){
var pn=ref.parentNode;
var _415=pn.childNodes;
var _416=false;
for(var i=0;i<_415.length;i++){
if((_415.item(i)["getAttribute"])&&(parseInt(_415.item(i).getAttribute("dojoinsertionindex"))>_414)){
this.before(node,_415.item(i));
_416=true;
break;
}
}
if(!_416){
this.before(node,ref);
}
};
this.textContent=function(node,text){
if(text){
this.replaceChildren(node,document.createTextNode(text));
return text;
}else{
var _418="";
if(node==null){
return _418;
}
for(var i=0;i<node.childNodes.length;i++){
switch(node.childNodes[i].nodeType){
case 1:
case 5:
_418+=dojo.xml.domUtil.textContent(node.childNodes[i]);
break;
case 3:
case 2:
case 4:
_418+=node.childNodes[i].nodeValue;
break;
default:
break;
}
}
return _418;
}
};
this.renderedTextContent=function(node){
var _419="";
if(node==null){
return _419;
}
for(var i=0;i<node.childNodes.length;i++){
switch(node.childNodes[i].nodeType){
case 1:
case 5:
switch(dojo.xml.domUtil.getStyle(node.childNodes[i],"display")){
case "block":
case "list-item":
case "run-in":
case "table":
case "table-row-group":
case "table-header-group":
case "table-footer-group":
case "table-row":
case "table-column-group":
case "table-column":
case "table-cell":
case "table-caption":
_419+="\n";
_419+=dojo.xml.domUtil.renderedTextContent(node.childNodes[i]);
_419+="\n";
break;
case "none":
break;
default:
_419+=dojo.xml.domUtil.renderedTextContent(node.childNodes[i]);
break;
}
break;
case 3:
case 2:
case 4:
var text=node.childNodes[i].nodeValue;
switch(dojo.xml.domUtil.getStyle(node,"text-transform")){
case "capitalize":
text=dojo.text.capitalize(text);
break;
case "uppercase":
text=text.toUpperCase();
break;
case "lowercase":
text=text.toLowerCase();
break;
default:
break;
}
switch(dojo.xml.domUtil.getStyle(node,"text-transform")){
case "nowrap":
break;
case "pre-wrap":
break;
case "pre-line":
break;
case "pre":
break;
default:
text=text.replace(/\s+/," ");
if(/\s$/.test(_419)){
text.replace(/^\s/,"");
}
break;
}
_419+=text;
break;
default:
break;
}
}
return _419;
};
this.remove=function(node){
if(node&&node.parentNode){
node.parentNode.removeChild(node);
}
};
};
dojo.provide("dojo.uri.Uri");
dojo.uri=new function(){
this.joinPath=function(){
var arr=[];
for(var i=0;i<arguments.length;i++){
arr.push(arguments[i]);
}
return arr.join("/").replace(/\/{2,}/g,"/").replace(/((https*|ftps*):)/i,"$1/");
};
this.dojoUri=function(uri){
return new dojo.uri.Uri(dojo.hostenv.getBaseScriptUri(),uri);
};
this.Uri=function(){
var uri=arguments[0];
for(var i=1;i<arguments.length;i++){
if(!arguments[i]){
continue;
}
var _420=new dojo.uri.Uri(arguments[i].toString());
var _421=new dojo.uri.Uri(uri.toString());
if(_420.path==""&&_420.scheme==null&&_420.authority==null&&_420.query==null){
if(_420.fragment!=null){
_421.fragment=_420.fragment;
}
_420=_421;
}else{
if(_420.scheme==null){
_420.scheme=_421.scheme;
if(_420.authority==null){
_420.authority=_421.authority;
if(_420.path.charAt(0)!="/"){
var path=_421.path.substring(0,_421.path.lastIndexOf("/")+1)+_420.path;
var segs=path.split("/");
for(var j=0;j<segs.length;j++){
if(segs[j]=="."){
if(j==segs.length-1){
segs[j]="";
}else{
segs.splice(j,1);
j--;
}
}else{
if(j>0&&!(j==1&&segs[0]=="")&&segs[j]==".."&&segs[j-1]!=".."){
if(j==segs.length-1){
segs.splice(j,1);
segs[j-1]="";
}else{
segs.splice(j-1,2);
j-=2;
}
}
}
}
_420.path=segs.join("/");
}
}
}
}
uri="";
if(_420.scheme!=null){
uri+=_420.scheme+":";
}
if(_420.authority!=null){
uri+="//"+_420.authority;
}
uri+=_420.path;
if(_420.query!=null){
uri+="?"+_420.query;
}
if(_420.fragment!=null){
uri+="#"+_420.fragment;
}
}
this.uri=uri.toString();
var _424="^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\\?([^#]*))?(#(.*))?$";
var r=this.uri.match(new RegExp(_424));
this.scheme=r[2]||(r[1]?"":null);
this.authority=r[4]||(r[3]?"":null);
this.path=r[5];
this.query=r[7]||(r[6]?"":null);
this.fragment=r[9]||(r[8]?"":null);
if(this.authority!=null){
_424="^((([^:]+:)?([^@]+))@)?([^:]*)(:([0-9]+))?$";
r=this.authority.match(new RegExp(_424));
this.user=r[3]||null;
this.password=r[4]||null;
this.host=r[5];
this.port=r[7]||null;
}
this.toString=function(){
return this.uri;
};
};
};
dojo.provide("dojo.xml.htmlUtil");
dojo.require("dojo.xml.domUtil");
dojo.require("dojo.text.String");
dojo.require("dojo.event.*");
dojo.require("dojo.uri.Uri");
dojo.xml.htmlUtil=new function(){
var _425=this;
var _426=false;
this.styleSheet=null;
this._clobberSelection=function(){
try{
if(window.getSelection){
var _427=window.getSelection();
_427.collapseToEnd();
}else{
if(document.selection){
document.selection.clear();
}
}
}
catch(e){
}
};
this.disableSelect=function(){
if(!_426){
_426=true;
var db=document.body;
if(dojo.render.html.moz){
db.style.MozUserSelect="none";
}else{
dojo.event.connect(db,"onselectstart",dojo.event.browser,"stopEvent");
dojo.event.connect(db,"ondragstart",dojo.event.browser,"stopEvent");
dojo.event.connect(db,"onmousemove",this,"_clobberSelection");
}
}
};
this.enableSelect=function(){
if(_426){
_426=false;
var db=document.body;
if(dojo.render.html.moz){
db.style.MozUserSelect="";
}else{
dojo.event.disconnect(db,"onselectstart",dojo.event.browser,"stopEvent");
dojo.event.disconnect(db,"ondragstart",dojo.event.browser,"stopEvent");
dojo.event.disconnect(db,"onmousemove",this,"_clobberSelection");
}
}
};
var cm=document["compatMode"];
var _430=((cm)&&((cm=="BackCompat")||(cm=="QuirksMode")))?true:false;
this.getInnerWidth=function(node){
return node.offsetWidth;
};
this.getOuterWidth=function(node){
dj_unimplemented("dojo.xml.htmlUtil.getOuterWidth");
};
this.getInnerHeight=function(node){
return node.offsetHeight;
};
this.getOuterHeight=function(node){
dj_unimplemented("dojo.xml.htmlUtil.getOuterHeight");
};
this.getTotalOffset=function(node,type){
var _431=(type=="top")?"offsetTop":"offsetLeft";
var alt=(type=="top")?"y":"x";
var ret=0;
if(node["offsetParent"]){
do{
ret+=node[_431];
node=node.offsetParent;
}while(node!=document.body.parentNode&&node!=null);
}else{
if(node[alt]){
ret+=node[alt];
}
}
return ret;
};
this.totalOffsetLeft=function(node){
return this.getTotalOffset(node,"left");
};
this.getAbsoluteX=this.totalOffsetLeft;
this.totalOffsetTop=function(node){
return this.getTotalOffset(node,"top");
};
this.getAbsoluteY=this.totalOffsetTop;
this.getEventTarget=function(evt){
if((window["event"])&&(event["srcElement"])){
return event.srcElement;
}else{
if((evt)&&(evt.target)){
return evt.target;
}
}
};
this.getScrollTop=function(){
return document.documentElement.scrollTop||document.body.scrollTop||0;
};
this.getScrollLeft=function(){
return document.documentElement.scrollLeft||document.body.scrollLeft||0;
};
this.evtTgt=this.getEventTarget;
this.getParentOfType=function(node,type){
var _433=node;
type=type.toLowerCase();
while(_433.nodeName.toLowerCase()!=type){
if((!_433)||(_433==(document["body"]||document["documentElement"]))){
return null;
}
_433=_433.parentNode;
}
return _433;
};
this.getAttribute=function(node,attr){
if((!node)||(!node.getAttribute)){
return null;
}
var ta=typeof attr=="string"?attr:new String(attr);
var v=node.getAttribute(ta.toUpperCase());
if((v)&&(typeof v=="string")&&(v!="")){
return v;
}
if(v&&typeof v=="object"&&v.value){
return v.value;
}
if((node.getAttributeNode)&&(node.getAttributeNode(ta))){
return (node.getAttributeNode(ta)).value;
}else{
if(node.getAttribute(ta)){
return node.getAttribute(ta);
}else{
if(node.getAttribute(ta.toLowerCase())){
return node.getAttribute(ta.toLowerCase());
}
}
}
return null;
};
this.getAttr=function(node,attr){
dj_deprecated("dojo.xml.htmlUtil.getAttr is deprecated, use dojo.xml.htmlUtil.getAttribute instead");
dojo.xml.htmlUtil.getAttribute(node,attr);
};
this.hasAttribute=function(node,attr){
var v=this.getAttribute(node,attr);
return v?true:false;
};
this.hasAttr=function(node,attr){
dj_deprecated("dojo.xml.htmlUtil.hasAttr is deprecated, use dojo.xml.htmlUtil.hasAttribute instead");
dojo.xml.htmlUtil.hasAttribute(node,attr);
};
this.getClass=function(node){
if(node.className){
return node.className;
}else{
if(this.hasAttribute(node,"class")){
return this.getAttribute(node,"class");
}
}
return "";
};
this.hasClass=function(node,_435){
var _436=this.getClass(node).split(/\s+/g);
for(var x=0;x<_436.length;x++){
if(_435==_436[x]){
return true;
}
}
return false;
};
this.prependClass=function(node,_437){
if(!node){
return null;
}
if(this.hasAttribute(node,"class")||node.className){
_437+=" "+(node.className||this.getAttribute(node,"class"));
}
return this.setClass(node,_437);
};
this.addClass=function(node,_438){
if(!node){
return null;
}
if(this.hasAttribute(node,"class")||node.className){
_438=(node.className||this.getAttribute(node,"class"))+" "+_438;
}
return this.setClass(node,_438);
};
this.setClass=function(node,_439){
if(!node){
return false;
}
var cs=new String(_439);
try{
if(typeof node.className=="string"){
node.className=cs;
}else{
if(node.setAttribute){
node.setAttribute("class",_439);
node.className=cs;
}else{
return false;
}
}
}
catch(e){
dj_debug("__util__.setClass() failed",e);
}
return true;
};
this.removeClass=function(node,_441){
if(!node){
return false;
}
var _441=dojo.text.trim(new String(_441));
try{
var cs=String(node.className).split(" ");
var nca=[];
for(var i=0;i<cs.length;i++){
if(cs[i]!=_441){
nca.push(cs[i]);
}
}
node.className=nca.join(" ");
}
catch(e){
dj_debug("__util__.removeClass() failed",e);
}
return true;
};
this.classMatchType={ContainsAll:0,ContainsAny:1,IsOnly:2};
this.getElementsByClass=function(_443,_444,_445,_446){
if(!_444){
_444=document;
}
var _447=_443.split(/\s+/g);
var _448=[];
if(_446!=1&&_446!=2){
_446=0;
}
if(false&&document.evaluate){
var _449="//"+(_445||"*")+"[contains(";
if(_446!=_425.classMatchType.ContainsAny){
_449+="concat(' ',@class,' '), ' "+_447.join(" ') and contains(concat(' ',@class,' '), ' ")+" ')]";
}else{
_449+="concat(' ',@class,' '), ' "+_447.join(" ')) or contains(concat(' ',@class,' '), ' ")+" ')]";
}
var _450=document.evaluate(_449,_444,null,XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE,null);
outer:
for(var node=null,i=0;node=_450.snapshotItem(i);i++){
if(_446!=_425.classMatchType.IsOnly){
_448.push(node);
}else{
if(!_425.getClass(node)){
continue outer;
}
var _451=_425.getClass(node).split(/\s+/g);
var _452=new RegExp("(\\s|^)("+_447.join(")|(")+")(\\s|$)");
for(var j=0;j<_451.length;j++){
if(!_451[j].match(_452)){
continue outer;
}
}
_448.push(node);
}
}
}else{
if(!_445){
_445="*";
}
var _453=_444.getElementsByTagName(_445);
outer:
for(var i=0;i<_453.length;i++){
var node=_453[i];
if(!_425.getClass(node)){
continue outer;
}
var _451=_425.getClass(node).split(/\s+/g);
var _452=new RegExp("(\\s|^)(("+_447.join(")|(")+"))(\\s|$)");
var _454=0;
for(var j=0;j<_451.length;j++){
if(_452.test(_451[j])){
if(_446==_425.classMatchType.ContainsAny){
_448.push(node);
continue outer;
}else{
_454++;
}
}else{
if(_446==_425.classMatchType.IsOnly){
continue outer;
}
}
}
if(_454==_447.length){
if(_446==_425.classMatchType.IsOnly&&_454==_451.length){
_448.push(node);
}else{
if(_446==_425.classMatchType.ContainsAll){
_448.push(node);
}
}
}
}
}
return _448;
};
this.getElementsByClassName=this.getElementsByClass;
this.setOpacity=function(node,_455,_456){
var h=dojo.render.html;
if(!_456){
if(_455>=1){
if(h.ie){
this.clearOpacity(node);
return;
}else{
_455=0.999999;
}
}else{
if(_455<0){
_455=0;
}
}
}
if(h.ie){
if(node.nodeName.toLowerCase()=="tr"){
var tds=node.getElementsByTagName("td");
for(var x=0;x<tds.length;x++){
tds[x].style.filter="Alpha(Opacity="+_455*100+")";
}
}
node.style.filter="Alpha(Opacity="+_455*100+")";
}else{
if(h.moz){
node.style.opacity=_455;
node.style.MozOpacity=_455;
}else{
if(h.safari){
node.style.opacity=_455;
node.style.KhtmlOpacity=_455;
}else{
node.style.opacity=_455;
}
}
}
};
this.getOpacity=function(node){
if(dojo.render.html.ie){
var opac=(node.filters&&node.filters.alpha&&typeof node.filters.alpha.opacity=="number"?node.filters.alpha.opacity:100)/100;
}else{
var opac=node.style.opacity||node.style.MozOpacity||node.style.KhtmlOpacity||1;
}
return opac>=0.999999?1:Number(opac);
};
this.clearOpacity=function(node){
var h=dojo.render.html;
if(h.ie){
if(node.filters&&node.filters.alpha){
node.style.filter="";
}
}else{
if(h.moz){
node.style.opacity=1;
node.style.MozOpacity=1;
}else{
if(h.safari){
node.style.opacity=1;
node.style.KhtmlOpacity=1;
}else{
node.style.opacity=1;
}
}
}
};
this.gravity=function(node,e){
var _460=e.pageX||e.clientX+document.body.scrollLeft;
var _461=e.pageY||e.clientY+document.body.scrollTop;
with(dojo.xml.htmlUtil){
var _462=getAbsoluteX(node)+(getInnerWidth(node)/2);
var _463=getAbsoluteY(node)+(getInnerHeight(node)/2);
}
with(arguments.callee){
return ((_460<_462?WEST:EAST)|(_461<_463?NORTH:SOUTH));
}
};
this.gravity.NORTH=1;
this.gravity.SOUTH=1<<1;
this.gravity.EAST=1<<2;
this.gravity.WEST=1<<3;
this.overElement=function(_464,e){
var _465=e.pageX||e.clientX+document.body.scrollLeft;
var _466=e.pageY||e.clientY+document.body.scrollTop;
with(dojo.xml.htmlUtil){
var top=getAbsoluteY(_464);
var _468=top+getInnerHeight(_464);
var left=getAbsoluteX(_464);
var _470=left+getInnerWidth(_464);
}
return (_465>=left&&_465<=_470&&_466>=top&&_466<=_468);
};
this.insertCssRule=function(_471,_472,_473){
if(dojo.render.html.ie){
if(!this.styleSheet){
}
if(!_473){
_473=this.styleSheet.rules.length;
}
return this.styleSheet.addRule(_471,_472,_473);
}else{
if(document.styleSheets[0]&&document.styleSheets[0].insertRule){
if(!this.styleSheet){
}
if(!_473){
_473=this.styleSheet.cssRules.length;
}
var rule=_471+"{"+_472+"}";
return this.styleSheet.insertRule(rule,_473);
}
}
};
this.insertCSSRule=function(_475,_476,_477){
dj_deprecated("dojo.xml.htmlUtil.insertCSSRule is deprecated, use dojo.xml.htmlUtil.insertCssRule instead");
dojo.xml.htmlUtil.insertCssRule(_475,_476,_477);
};
this.removeCssRule=function(_478){
if(!this.styleSheet){
dj_debug("no stylesheet defined for removing rules");
return false;
}
if(dojo.render.html.ie){
if(!_478){
_478=this.styleSheet.rules.length;
this.styleSheet.removeRule(_478);
}
}else{
if(document.styleSheets[0]){
if(!_478){
_478=this.styleSheet.cssRules.length;
}
this.styleSheet.deleteRule(_478);
}
}
return true;
};
this.removeCSSRule=function(_479){
dj_deprecated("dojo.xml.htmlUtil.removeCSSRule is deprecated, use dojo.xml.htmlUtil.removeCssRule instead");
dojo.xml.htmlUtil.removeCssRule(_479);
};
this.insertCssFile=function(URI,doc,_482){
if(!URI){
return;
}
if(!doc){
doc=document;
}
if(doc.baseURI){
URI=new dojo.uri.Uri(doc.baseURI,URI);
}
if(_482&&doc.styleSheets){
var loc=location.href.split("#")[0].substring(0,location.href.indexOf(location.pathname));
for(var i=0;i<doc.styleSheets.length;i++){
if(doc.styleSheets[i].href&&URI==new dojo.uri.Uri(doc.styleSheets[i].href)){
return;
}
}
}
var file=doc.createElement("link");
file.setAttribute("type","text/css");
file.setAttribute("rel","stylesheet");
file.setAttribute("href",URI);
var head=doc.getElementsByTagName("head")[0];
head.appendChild(file);
};
this.insertCSSFile=function(URI,doc,_486){
dj_deprecated("dojo.xml.htmlUtil.insertCSSFile is deprecated, use dojo.xml.htmlUtil.insertCssFile instead");
dojo.xml.htmlUtil.insertCssFile(URI,doc,_486);
};
this.getBackgroundColor=function(node){
var _487;
do{
_487=dojo.xml.domUtil.getStyle(node,"background-color");
if(_487.toLowerCase()=="rgba(0, 0, 0, 0)"){
_487="transparent";
}
if(node==document.body){
node=null;
break;
}
node=node.parentNode;
}while(node&&_487=="transparent");
if(_487=="transparent"){
_487=[255,255,255,0];
}else{
_487=dojo.xml.domUtil.extractRGB(_487);
}
return _487;
};
this.getUniqueId=function(){
return dojo.xml.domUtil.getUniqueId();
};
this.getStyle=function(el,css){
dojo.xml.domUtil.getStyle(el,css);
};
};
dojo.provide("dojo.graphics.htmlEffects");
dojo.require("dojo.animation.*");
dojo.require("dojo.xml.domUtil");
dojo.require("dojo.xml.htmlUtil");
dojo.require("dojo.event.*");
dojo.require("dojo.alg.*");
dojo.graphics.htmlEffects=new function(){
this.fadeOut=function(node,_489,_490){
return this.fade(node,_489,dojo.xml.htmlUtil.getOpacity(node),0,_490);
};
this.fadeIn=function(node,_491,_492){
return this.fade(node,_491,dojo.xml.htmlUtil.getOpacity(node),1,_492);
};
this.fadeHide=function(node,_493,_494){
if(!_493){
_493=150;
}
return this.fadeOut(node,_493,function(node){
node.style.display="none";
if(typeof _494=="function"){
_494(node);
}
});
};
this.fadeShow=function(node,_495,_496){
if(!_495){
_495=150;
}
node.style.display="block";
return this.fade(node,_495,0,1,_496);
};
this.fade=function(node,_497,_498,_499,_500){
var anim=new dojo.animation.Animation(new dojo.math.curves.Line([_498],[_499]),_497,0);
dojo.event.connect(anim,"onAnimate",function(e){
dojo.xml.htmlUtil.setOpacity(node,e.x);
});
if(_500){
dojo.event.connect(anim,"onEnd",function(e){
_500(node,anim);
});
}
anim.play(true);
return anim;
};
this.slideTo=function(node,_501,_502,_503){
return this.slide(node,[node.offsetLeft,node.offsetTop],_501,_502,_503);
};
this.slideBy=function(node,_504,_505,_506){
return this.slideTo(node,[node.offsetLeft+_504[0],node.offsetTop+_504[1]],_505,_506);
};
this.slide=function(node,_507,_508,_509,_510){
var anim=new dojo.animation.Animation(new dojo.math.curves.Line(_507,_508),_509,0);
dojo.event.connect(anim,"onAnimate",function(e){
with(node.style){
left=e.x+"px";
top=e.y+"px";
}
});
if(_510){
dojo.event.connect(anim,"onEnd",function(e){
_510(node,anim);
});
}
anim.play(true);
return anim;
};
this.colorFadeIn=function(node,_511,_512,_513,_514){
var _515=dojo.xml.htmlUtil.getBackgroundColor(node);
var bg=dojo.xml.domUtil.getStyle(node,"background-color").toLowerCase();
var _517=bg=="transparent"||bg=="rgba(0, 0, 0, 0)";
while(_515.length>3){
_515.pop();
}
while(_511.length>3){
_511.pop();
}
var anim=this.colorFade(node,_511,_515,_512,_514,true);
dojo.event.connect(anim,"onEnd",function(e){
if(_517){
node.style.backgroundColor="transparent";
}
});
if(_513>0){
node.style.backgroundColor="rgb("+_511.join(",")+")";
setTimeout(function(){
anim.play(true);
},_513);
}else{
anim.play(true);
}
return anim;
};
this.highlight=this.colorFadeIn;
this.colorFadeFrom=this.colorFadeIn;
this.colorFadeOut=function(node,_518,_519,_520,_521){
var _522=dojo.xml.htmlUtil.getBackgroundColor(node);
while(_522.length>3){
_522.pop();
}
while(_518.length>3){
_518.pop();
}
var anim=this.colorFade(node,_522,_518,_519,_521,_520>0);
if(_520>0){
node.style.backgroundColor="rgb("+_522.join(",")+")";
setTimeout(function(){
anim.play(true);
},_520);
}
return anim;
};
this.unhighlight=this.colorFadeOut;
this.colorFadeTo=this.colorFadeOut;
this.colorFade=function(node,_523,_524,_525,_526,_527){
while(_523.length>3){
_523.pop();
}
while(_524.length>3){
_524.pop();
}
var anim=new dojo.animation.Animation(new dojo.math.curves.Line(_523,_524),_525,0);
dojo.event.connect(anim,"onAnimate",function(e){
node.style.backgroundColor="rgb("+e.coordsAsInts().join(",")+")";
});
if(_526){
dojo.event.connect(anim,"onEnd",function(e){
_526(node,anim);
});
}
if(!_527){
anim.play(true);
}
return anim;
};
this.wipeIn=function(node,_528,_529,_530){
var _531=dojo.xml.htmlUtil.getStyle(node,"overflow");
var _532=dojo.xml.htmlUtil.getStyle(node,"height");
node.style.display=dojo.alg.inArray(node.tagName.toLowerCase(),["tr","td","th"])?"":"block";
var _533=node.offsetHeight;
if(_531=="visible"){
node.style.overflow="hidden";
}
node.style.height=0;
var anim=new dojo.animation.Animation(new dojo.math.curves.Line([0],[_533]),_528,0);
dojo.event.connect(anim,"onAnimate",function(e){
node.style.height=Math.round(e.x)+"px";
});
dojo.event.connect(anim,"onEnd",function(e){
if(_531!="visible"){
node.style.overflow=_531;
}
node.style.height=_532;
if(_529){
_529(node,anim);
}
});
if(!_530){
anim.play(true);
}
return anim;
};
this.wipeOut=function(node,_534,_535,_536){
var _537=dojo.xml.htmlUtil.getStyle(node,"overflow");
var _538=dojo.xml.htmlUtil.getStyle(node,"height");
var _539=node.offsetHeight;
node.style.overflow="hidden";
var anim=new dojo.animation.Animation(new dojo.math.curves.Line([_539],[0]),_534,0);
dojo.event.connect(anim,"onAnimate",function(e){
node.style.height=Math.round(e.x)+"px";
});
dojo.event.connect(anim,"onEnd",function(e){
node.style.display="none";
node.style.overflow=_537;
node.style.height=_538;
if(_535){
_535(node,anim);
}
});
if(!_536){
anim.play(true);
}
return anim;
};
this.explode=function(_540,_541,_542,_543){
var _544=[dojo.xml.htmlUtil.getAbsoluteX(_540),dojo.xml.htmlUtil.getAbsoluteY(_540),dojo.xml.htmlUtil.getInnerWidth(_540),dojo.xml.htmlUtil.getInnerHeight(_540)];
return this.explodeFromBox(_544,_541,_542,_543);
};
this.explodeFromBox=function(_545,_546,_547,_548){
var _549=document.createElement("div");
with(_549.style){
position="absolute";
border="1px solid black";
display="none";
}
document.body.appendChild(_549);
with(_546.style){
visibility="hidden";
display="block";
}
var _550=[dojo.xml.htmlUtil.getAbsoluteX(_546),dojo.xml.htmlUtil.getAbsoluteY(_546),dojo.xml.htmlUtil.getInnerWidth(_546),dojo.xml.htmlUtil.getInnerHeight(_546)];
with(_546.style){
display="none";
visibility="visible";
}
var anim=new dojo.animation.Animation(new dojo.math.curves.Line(_545,_550),_547,0);
dojo.event.connect(anim,"onBegin",function(e){
_549.style.display="block";
});
dojo.event.connect(anim,"onAnimate",function(e){
with(_549.style){
left=e.x+"px";
top=e.y+"px";
width=e.coords[2]+"px";
height=e.coords[3]+"px";
}
});
dojo.event.connect(anim,"onEnd",function(){
_546.style.display="block";
_549.parentNode.removeChild(_549);
if(_548){
_548(_546,anim);
}
});
anim.play();
return anim;
};
this.implode=function(_551,_552,_553,_554){
var _555=[dojo.xml.htmlUtil.getAbsoluteX(_552),dojo.xml.htmlUtil.getAbsoluteY(_552),dojo.xml.htmlUtil.getInnerWidth(_552),dojo.xml.htmlUtil.getInnerHeight(_552)];
return this.implodeToBox(_551,_555,_553,_554);
};
this.implodeToBox=function(_556,_557,_558,_559){
var _560=document.createElement("div");
with(_560.style){
position="absolute";
border="1px solid black";
display="none";
}
document.body.appendChild(_560);
var anim=new dojo.animation.Animation(new dojo.math.curves.Line([dojo.xml.htmlUtil.getAbsoluteX(_556),dojo.xml.htmlUtil.getAbsoluteY(_556),dojo.xml.htmlUtil.getInnerWidth(_556),dojo.xml.htmlUtil.getInnerHeight(_556)],_557),_558,0);
dojo.event.connect(anim,"onBegin",function(e){
_556.style.display="none";
_560.style.display="block";
});
dojo.event.connect(anim,"onAnimate",function(e){
with(_560.style){
left=e.x+"px";
top=e.y+"px";
width=e.coords[2]+"px";
height=e.coords[3]+"px";
}
});
dojo.event.connect(anim,"onEnd",function(){
_560.parentNode.removeChild(_560);
if(_559){
_559(_556,anim);
}
});
anim.play();
return anim;
};
};
dojo.graphics.htmlEffects.Exploder=function(_561,_562){
var _563=this;
this.waitToHide=500;
this.timeToShow=100;
this.waitToShow=200;
this.timeToHide=70;
this.autoShow=false;
this.autoHide=false;
var _564=null;
var _565=null;
var _566=null;
var _567=null;
var _568=null;
var _569=null;
this.showing=false;
this.onBeforeExplode=null;
this.onAfterExplode=null;
this.onBeforeImplode=null;
this.onAfterImplode=null;
this.onExploding=null;
this.onImploding=null;
this.timeShow=function(){
clearTimeout(_566);
_566=setTimeout(_563.show,_563.waitToShow);
};
this.show=function(){
clearTimeout(_566);
clearTimeout(_567);
if((_565&&_565.status()=="playing")||(_564&&_564.status()=="playing")||_563.showing){
return;
}
if(typeof _563.onBeforeExplode=="function"){
_563.onBeforeExplode(_561,_562);
}
_564=dojo.graphics.htmlEffects.explode(_561,_562,_563.timeToShow,function(e){
_563.showing=true;
if(typeof _563.onAfterExplode=="function"){
_563.onAfterExplode(_561,_562);
}
});
if(typeof _563.onExploding=="function"){
dojo.event.connect(_564,"onAnimate",this,"onExploding");
}
};
this.timeHide=function(){
clearTimeout(_566);
clearTimeout(_567);
if(_563.showing){
_567=setTimeout(_563.hide,_563.waitToHide);
}
};
this.hide=function(){
clearTimeout(_566);
clearTimeout(_567);
if(_564&&_564.status()=="playing"){
return;
}
_563.showing=false;
if(typeof _563.onBeforeImplode=="function"){
_563.onBeforeImplode(_561,_562);
}
_565=dojo.graphics.htmlEffects.implode(_562,_561,_563.timeToHide,function(e){
if(typeof _563.onAfterImplode=="function"){
_563.onAfterImplode(_561,_562);
}
});
if(typeof _563.onImploding=="function"){
dojo.event.connect(_565,"onAnimate",this,"onImploding");
}
};
dojo.event.connect(_561,"onclick",function(e){
if(_563.showing){
_563.hide();
}else{
_563.show();
}
});
dojo.event.connect(_561,"onmouseover",function(e){
if(_563.autoShow){
_563.timeShow();
}
});
dojo.event.connect(_561,"onmouseout",function(e){
if(_563.autoHide){
_563.timeHide();
}
});
dojo.event.connect(_562,"onmouseover",function(e){
clearTimeout(_567);
});
dojo.event.connect(_562,"onmouseout",function(e){
if(_563.autoHide){
_563.timeHide();
}
});
dojo.event.connect(document.documentElement||document.body,"onclick",function(e){
if(_563.autoHide&&_563.showing&&!dojo.xml.domUtil.isChildOf(e.target,_562)&&!dojo.xml.domUtil.isChildOf(e.target,_561)){
_563.hide();
}
});
return this;
};
dojo.hostenv.conditionalLoadModule({browser:["dojo.graphics.htmlEffects"]});
dojo.hostenv.moduleLoaded("dojo.graphics.*");

