/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.dnd.HtmlDragManager");
dojo.require("dojo.event.*");
dojo.require("dojo.alg.*");
dojo.require("dojo.xml.htmlUtil");

// NOTE: there will only ever be a single instance of HTMLDragManager, so it's
// safe to use prototype properties for book-keeping.
dojo.dnd.HtmlDragManager = function(){
}

dj_inherits(dojo.dnd.HtmlDragManager, dojo.dnd.DragManager);

dojo.lang.extend(dojo.dnd.HtmlDragManager, {
	/**
	 * There are several sets of actions that the DnD code cares about in the
	 * HTML context:
	 *	1.) mouse-down ->
	 *			(draggable selection)
	 *			(dragObject generation)
	 *		mouse-move ->
	 *			(draggable movement)
	 *			(droppable detection)
	 *			(inform droppable)
	 *			(inform dragObject)
	 *		mouse-up
	 *			(inform/destroy dragObject)
	 *			(inform draggable)
	 *			(inform droppable)
	 *	2.) mouse-down -> mouse-down
	 *			(click-hold context menu)
	 *	3.) mouse-click ->
	 *			(draggable selection)
	 *		shift-mouse-click ->
	 *			(augment draggable selection)
	 *		mouse-down ->
	 *			(dragObject generation)
	 *		mouse-move ->
	 *			(draggable movement)
	 *			(droppable detection)
	 *			(inform droppable)
	 *			(inform dragObject)
	 *		mouse-up
	 *			(inform draggable)
	 *			(inform droppable)
	 *	4.) mouse-up
	 *			(clobber draggable selection)
	 */
	mouseDownTimer: null, // used for click-hold operations
	dsCounter: 0,
	dsPrefix: "dojoDragSource",

	// dimension calculation cache for use durring drag
	dropTargetDimensions: [],

	currentDropTarget: null,
	currentDropTargetPoints: null,
	previousDropTarget: null,

	// mouse position properties
	currentX: null,
	currentY: null,
	lastX: null,
	lastY: null,
	mouseDownX: null,
	mouseDownY: null,

	dropAcceptable: false,

	// method over-rides
	registerDragSource: function(ds){
		// FIXME: dragSource objects SHOULD have some sort of property that
		// references their DOM node, we shouldn't just be passing nodes and
		// expecting it to work.
		var dp = this.dsPrefix;
		var dpIdx = dp+"Idx_"+(this.dsCounter++);
		ds.dragSourceId = dpIdx;
		this.dragSources[dpIdx] = ds;
		ds.domNode.setAttribute(dp, dpIdx);
	},

	registerDropTarget: function(dt){
		this.dropTargets.push(dt);
	},

	getDragSource: function(e){
		var tn = e.target;
		if(tn === document.body){ return; }
		var ta = dojo.xml.htmlUtil.getAttribute(tn, this.dsPrefix);
		while((!ta)&&(tn)){
			tn = tn.parentNode;
			if((!tn)||(tn === document.body)){ return; }
			ta = dojo.xml.htmlUtil.getAttribute(tn, this.dsPrefix);
		}
		return this.dragSources[ta];
	},

	onKeyDown: function(e){
	},

	onMouseDown: function(e){
		// find a selection object, if one is a parent of the source node
		var ds = this.getDragSource(e);
		if(!ds){ return; }
		if(!dojo.alg.inArray(this.selectedSources, ds)){
			this.selectedSources.push(ds);
		}
		//e.preventDefault();
		dojo.event.connect(document, "onmousemove", this, "onMouseMove");
	},

	onMouseUp: function(e){
		var _this = this;
		if((!e.shiftKey)&&(!e.ctrlKey)){
			dojo.alg.forEach(this.dragObjects, function(tempDragObj){
				var ret = null;
				if(!tempDragObj){ return; }
				if(_this.currentDropTarget) {
					e.dragObject = tempDragObj;
	
					// NOTE: we can't get anything but the current drop target
					// here since the drag shadow blocks mouse-over events.
					// This is probelematic for dropping "in" something
					var ce = _this.currentDropTarget.domNode.childNodes;
					if(ce.length > 0){
						e.dropTarget = ce[0];
						while(e.dropTarget == tempDragObj.domNode){
							e.dropTarget = e.dropTarget.nextSibling;
						}
					}else{
						e.dropTarget = _this.currentDropTarget.domNode;
					}
					if (_this.dropAcceptable){
						ret = _this.currentDropTarget.onDrop(e);
					} else {
						 _this.currentDropTarget.onDragOut(e);
					}
				}
				tempDragObj.onDragEnd({
					dragStatus: (_this.dropAcceptable && ret) ? "dropSuccess" : "dropFailure"
				});
			});
						
			this.selectedSources = [];
			this.dragObjects = [];
		}
		dojo.event.disconnect(document, "onmousemove", this, "onMouseMove");
		this.currentDropTarget = null;
		this.currentDropTargetPoints = null;
	},

	onMouseMove: function(e){
		var _this = this;
		// if we've got some sources, but no drag objects, we need to send
		// onDragStart to all the right parties and get things lined up for
		// drop target detection
		if((this.selectedSources.length)&&(!this.dragObjects.length)){
			dojo.alg.forEach(this.selectedSources, function(tempSource){
				if(!tempSource){ return; }
				var tdo = tempSource.onDragStart(e);
				if(tdo){
					tdo.onDragStart(e);
					_this.dragObjects.push(tdo);
				}
			});


			this.dropTargetDimensions = [];
			dojo.alg.forEach(this.dropTargets, function(tempTarget){
				var hu = dojo.xml.htmlUtil;
				var tn = tempTarget.domNode;
				var ttx = hu.getAbsoluteX(tn);
				var tty = hu.getAbsoluteY(tn);
				_this.dropTargetDimensions.push([
					[ttx, tty],	// upper-left
					// lower-right
					[ ttx+hu.getInnerWidth(tn), tty+hu.getInnerHeight(tn) ],
					tempTarget
				]);
			});
		}
		dojo.alg.forEach(this.dragObjects, function(tempDragObj){
			if(!tempDragObj){ return; }
			tempDragObj.onDragMove(e);
		});

		// if we have a current drop target, check to see if we're outside of
		// it. If so, do all the actions that need doing.
		var dtp = this.currentDropTargetPoints;
		if((dtp)&&(_this.isInsideBox(e, dtp))){
			this.currentDropTarget.onDragMove(e);
		}else{
			// FIXME: need to fix the event object!
			if(this.currentDropTarget){
				this.currentDropTarget.onDragOut(e);
			}

			this.currentDropTarget = null;
			this.currentDropTargetPoints = null;
			this.dropAcceptable = false;

			// check the mouse position to see if we're in a drop target
			dojo.alg.forEach(this.dropTargetDimensions, function(tmpDA){
				// FIXME: is there a way to shortcut this?
				if((!_this.currentDropTarget)&&(_this.isInsideBox(e, tmpDA))){
					_this.currentDropTarget = tmpDA[2];
					_this.currentDropTargetPoints = tmpDA;
					return "break";
				}
			});
			e.dragObjects = this.dragObjects;
			if(this.currentDropTarget){
				this.dropAcceptable = this.currentDropTarget.onDragOver(e);
			}
		}
	},

	isInsideBox: function(e, coords){
		if(	(e.clientX > coords[0][0])&&
			(e.clientX < coords[1][0])&&
			(e.clientY > coords[0][1])&&
			(e.clientY < coords[1][1]) ){
			return true;
		}
		return false;
	},

	onMouseOver: function(e){
	},
	
	onMouseOut: function(e){
	}
});

dojo.dnd.dragManager = new dojo.dnd.HtmlDragManager();

// global namespace protection closure
(function(){
	var d = document;
	var dm = dojo.dnd.dragManager;
	// set up event handlers on the document
	dojo.event.connect(d, "onkeydown", 		dm, "onKeyDown");
	dojo.event.connect(d, "onmouseover",	dm, "onMouseOver");
	dojo.event.connect(d, "onmouseout", 	dm, "onMouseOut");
	dojo.event.connect(d, "onmousedown",	dm, "onMouseDown");
	dojo.event.connect(d, "onmouseup",		dm, "onMouseUp");
})();
