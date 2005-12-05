/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.xml.Parse");

dojo.require("dojo.xml.domUtil");

//TODO: determine dependencies
// currently has dependency on dojo.xml.DomUtil nodeTypes constants...

/* generic method for taking a node and parsing it into an object

TODO: WARNING: This comment is wrong!

For example, the following xml fragment

<foo bar="bar">
	<baz xyzzy="xyzzy"/>
</foo>

can be described as:

dojo.???.foo = {}
dojo.???.foo.bar = {}
dojo.???.foo.bar.value = "bar";
dojo.???.foo.baz = {}
dojo.???.foo.baz.xyzzy = {}
dojo.???.foo.baz.xyzzy.value = "xyzzy"

*/
// using documentFragment nomenclature to generalize in case we don't want to require passing a collection of nodes with a single parent
dojo.xml.Parse = function(){
	this.parseFragment = function(documentFragment) {
		// handle parent element
		var parsedFragment = {};
		// var tagName = dojo.xml.domUtil.getTagName(node);
		var tagName = dojo.xml.domUtil.getTagName(documentFragment);
		// TODO: What if document fragment is just text... need to check for nodeType perhaps?
		parsedFragment[tagName] = new Array(documentFragment.tagName);
		var attributeSet = this.parseAttributes(documentFragment);
		for(var attr in attributeSet){
			if(!parsedFragment[attr]){
				parsedFragment[attr] = [];
			}
			parsedFragment[attr][parsedFragment[attr].length] = attributeSet[attr];
		}
		var nodes = documentFragment.childNodes;
		for(var childNode in nodes){
			switch(nodes[childNode].nodeType){
				case  dojo.xml.domUtil.nodeTypes.ELEMENT_NODE: // element nodes, call this function recursively
					parsedFragment[tagName].push(this.parseElement(nodes[childNode]));
					break;
				case  dojo.xml.domUtil.nodeTypes.TEXT_NODE: // if a single text node is the child, treat it as an attribute
					if(nodes.length == 1){
						if(!parsedFragment[documentFragment.tagName]){
							parsedFragment[tagName] = [];
						}
						parsedFragment[tagName].push({ value: nodes[0].nodeValue });
					}
					break;
			}
		}
		
		return parsedFragment;
	}

	this.parseElement = function(node, hasParentNodeSet, optimizeForDojoML, thisIdx){
		// TODO: make this namespace aware
		var parsedNodeSet = {};
		var tagName = dojo.xml.domUtil.getTagName(node);
		parsedNodeSet[tagName] = [];
		if((!optimizeForDojoML)||(tagName.substr(0,4).toLowerCase()=="dojo")){
			var attributeSet = this.parseAttributes(node);
			for(var attr in attributeSet){
				if(!parsedNodeSet[tagName][attr]){
					parsedNodeSet[tagName][attr] = [];
				}
				parsedNodeSet[tagName][attr].push(attributeSet[attr]);
			}
		}
	
		// FIXME: we might want to make this optional or provide cloning instead of
		// referencing, but for now, we include a node reference to allow
		// instantiated components to figure out their "roots"
		parsedNodeSet[tagName].nodeRef = node;
		parsedNodeSet.tagName = tagName;
		parsedNodeSet.index = thisIdx||0;
	
		var ntypes = dojo.xml.domUtil.nodeTypes;
	
		var count = 0;
		for(var i=0; i<node.childNodes.length; i++){
			var tcn = node.childNodes.item(i);
			switch(tcn.nodeType){
				case  ntypes.ELEMENT_NODE: // element nodes, call this function recursively
					count++;
					var ctn = dojo.xml.domUtil.getTagName(tcn);
					if(!parsedNodeSet[ctn]){
						parsedNodeSet[ctn] = [];
					}
					parsedNodeSet[ctn].push(this.parseElement(tcn, true, optimizeForDojoML, count));
					if(	(tcn.childNodes.length == 1)&&
						(tcn.childNodes.item(0).nodeType == ntypes.TEXT_NODE)){
						parsedNodeSet[ctn][parsedNodeSet[ctn].length-1].value = tcn.childNodes.item(0).nodeValue;
					}
					break;
				case  ntypes.TEXT_NODE: // if a single text node is the child, treat it as an attribute
					if(node.childNodes.length == 1) {
						parsedNodeSet[tagName].push({ value: node.childNodes.item(0).nodeValue });
					}
					break;
				default: break;
				/*
				case  ntypes.ATTRIBUTE_NODE: // attribute node... not meaningful here
					break;
				case  ntypes.CDATA_SECTION_NODE: // cdata section... not sure if this would ever be meaningful... might be...
					break;
				case  ntypes.ENTITY_REFERENCE_NODE: // entity reference node... not meaningful here
					break;
				case  ntypes.ENTITY_NODE: // entity node... not sure if this would ever be meaningful
					break;
				case  ntypes.PROCESSING_INSTRUCTION_NODE: // processing instruction node... not meaningful here
					break;
				case  ntypes.COMMENT_NODE: // comment node... not not sure if this would ever be meaningful 
					break;
				case  ntypes.DOCUMENT_NODE: // document node... not sure if this would ever be meaningful
					break;
				case  ntypes.DOCUMENT_TYPE_NODE: // document type node... not meaningful here
					break;
				case  ntypes.DOCUMENT_FRAGMENT_NODE: // document fragment node... not meaningful here
					break;
				case  ntypes.NOTATION_NODE:// notation node... not meaningful here
					break;
				*/
			}
		}
		//return (hasParentNodeSet) ? parsedNodeSet[node.tagName] : parsedNodeSet;
		return parsedNodeSet;
	}

	/* parses a set of attributes on a node into an object tree */
	this.parseAttributes = function(node) {
		// TODO: make this namespace aware
		var parsedAttributeSet = {};
		var atts = node.attributes;
		// TODO: should we allow for duplicate attributes at this point...
		// would any of the relevant dom implementations even allow this?
		for(var i=0; i<atts.length; i++) {
			var attnode = atts.item(i);
			if((dojo.render.html.capable)&&(dojo.render.html.ie)){
				if(!attnode){ continue; }
				if(	(typeof attnode == "object")&&
					(typeof attnode.nodeValue == 'undefined')||
					(attnode.nodeValue == null)||
					(attnode.nodeValue == '')){ 
					continue; 
				}
			}
			parsedAttributeSet[attnode.nodeName] = { 
				value: attnode.nodeValue 
			};
		}
		return parsedAttributeSet;
	}
}
