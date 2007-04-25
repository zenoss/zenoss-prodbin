
var Class={
    create:function(){
        return function(){
            this.__init__.apply(this,arguments);
        }
    }
}

var isManager = true;

var ZenGridLoadingMsg = Class.create();
ZenGridLoadingMsg.prototype = {
    __init__: function(msg) {
        bindMethods(this);
        this.framework = DIV(
            {'class':'zengridload_container'},
            [
            //top row
            DIV({'class':'dbox_tl'},
             [ DIV({'class':'dbox_tr'},
               [ DIV({'class':'dbox_tc'}, null)])]),
            //middle row
            DIV({'class':'dbox_ml'},
             [ DIV({'class':'dbox_mr'},
               [ DIV({'class':'dbox_mc',
                      'id':'zengridload_content'}, msg)])]),
            //bottom row
            DIV({'class':'dbox_bl'},
             [ DIV({'class':'dbox_br'},
               [ DIV({'class':'dbox_bc'}, null)])])
            ]);
        appendChildNodes(currentDocument().body, this.framework);
        setStyle(this.framework, {
            'width':'15em',
            'position':'absolute',
            'z-index':'11000',
            'top':'0',
            'left':'100',
            'visibility':'visible'
        });
        setStyle($('zengridload_content'), {
            'font-weight':'bold',
            'font-size':'2em',
            'text-align':'center'

        });

    },
    show: function() {
        setStyle(this.framework, {'visibility':'visible'});
    },
    hide: function() {
        setStyle(this.framework, {'visibility':'hidden'});
    }
}
var ZenGridBuffer = Class.create();

ZenGridBuffer.prototype = {
    __init__: function(url) {
        this.startPos = 0;
        this.size = 0;
        this.rows = new Array();
        this.updating = false;
        this.lastOffset = 0;
        this.maxQuery = 300;
        this.totalRows = 0;
        this.numRows = 0;
        this.numCols = 0;
        this.pageSize = 15;
        this.bufferSize = 5; 
        this.marginFactor = 0.15; 
        bindMethods(this);
    },
    setNumCols: function(n) {this.numCols = n;},
    setNumRows: function(n) {this.numRows = n;},
    tolerance: function() {
        return parseInt(this.bufferSize * this.pageSize * this.marginFactor);
    },
    endPos: function() {return this.startPos + this.rows.length;},
    closeToTop: function(pos) {
        return pos - this.startPos < this.tolerance();
    },
    closeToBottom: function(pos) {
        return this.endPos() - (pos + this.pageSize) < this.tolerance();
    },
    isNearLimit: function(pos) {
        return (!this.isAtTop() && this.closeToTop(pos)) ||
               (!this.isAtBottom() && this.closeToBottom(pos));
    },
    isAtTop: function() { return this.startPos == 0; },
    isAtBottom: function() { return this.endPos() == this.numRows; },
    querySize: function(offset) {
        var newOffset = this.queryOffset(offset);
        var newSize = 0;
        if (newOffset>=this.startPos) {
            var endOffset = this.maxQuery + newOffset;
            if (endOffset > this.numRows)
                endOffset = this.totalRows;
            newSize = endOffset - newOffset;
                if(newOffset==0&&newSize<this.maxQuery){
                    newSize = this.maxQuery;
                }
        } else {
            var newSize = this.startPos - newOffset;
            if (newSize > this.maxQuery)
                newSize = this.maxQuery;
        }
        if (newSize > this.maxQuery)
            newSize = this.maxQuery;
        return newSize;
    },
    queryOffset: function(offset) {
        var newOffset = offset;
        if (offset > this.startPos) {
            newOffset = offset>this.endPos()?offset:this.endPos();
        } else {
            if (offset + this.maxQuery>=this.startPos) {
                newOffset = this.startPos - this.maxQuery;
                if (newOffset<0) newOffset = 0;
            }
        }
        this.lastOffset = newOffset;
        return newOffset;
    },
    getRows: function(start, count) {
        var sPos = start - this.startPos;
        var ePos = sPos + count;
        if (ePos>this.size) ePos = this.size;
        var results = new Array();
        var index = 0;
        for( i = sPos; i<ePos; i++){
            results[index++] = this.rows[i]
        };
        return results;
    },
    loadRows: function(response) {
        var rows = response;
        return rows;
    },
    update: function(response, start) {
        var newRows = this.loadRows(response);
        if (this.rows.length == 0) {
            this.rows = newRows;
            this.size = this.rows.length;
            //this.startPos = start;
            return;
        }
        if (start > this.startPos) { 
            if (this.startPos + this.rows.length < start) {
                this.rows =  newRows;
                this.startPos = start;
             } else {
                 this.rows = this.rows.concat( newRows.slice(0, newRows.length));
                 if (this.rows.length > this.maxQuery) {
                    var fullSize = this.rows.length;
                    this.rows = this.rows.slice(this.rows.length - 
                        this.maxQuery, this.rows.length);
                    this.startPos = this.startPos +  (fullSize - this.rows.length);
                 }
             }
           } else { 
             if (start + newRows.length < this.startPos) {
                this.rows =  newRows;
         } else {
            this.rows = newRows.slice(0, this.startPos).concat(this.rows);
            if (this.rows.length > this.maxQuery) 
               this.rows = this.rows.slice(0, this.maxQuery)
         }
         this.startPos =  start;
      }
      this.size = this.rows.length;
      //this.startPos = start;

    },
    clear: function() {
        this.rows = new Array();
        this.startPos = 0;
        this.size = 0;
    }
}


var ZenGrid = Class.create();

ZenGrid.prototype = {
    __init__: function(container, url, gridId, buffer, isHistory) {
        bindMethods(this);
        this.isHistory = isHistory || 0;
        this.container = $(container);
        this.gridId = gridId;
        this.buffer = buffer;
        this.numRows = 15;
        this.rowHeight = 32;
        this.checkedArray = new Array();
        this.url = url;
        this.lastparams = {};
        this.fields = [];
        this.lastOffset = 0;
        this.lastPixelOffset = this.lastPixelOffset || 0;
        this.fontProportion = this.getFontProportion();
        this.buildHTML();
        this.clearFirst = false;
        this.lock = new DeferredLock();
        this.scrollTimeout = null;
        this.loadingbox = new ZenGridLoadingMsg('Loading...');
        fieldlock = this.lock.acquire();
        fieldlock.addCallback(this.refreshFields);
        updatelock = this.lock.acquire();
        updatelock.addCallback(bind(function(r){
            this.refreshTable(this.lastOffset);
            this.lock.release();
        }, this));
        this.addMouseWheelListening();
        connect(this.scrollbar, 'onscroll', this.handleScroll);
    },
    getFontProportion: function() {
        var x = SPAN({class:'ruler'}, 
            'abcdefghijklmnopqrstuvwxyz');
        appendChildNodes(document.body, x);
        var myw = getElementDimensions(x).w/26;
        removeElement(x);
        return myw;
    },
    addMouseWheelListening: function() {
        if (this.container.addEventListener)
                this.container.addEventListener(
                    'DOMMouseScroll', this.handleWheel, false);
        this.container.onmousewheel = this.handleWheel;
    },
    handleWheel: function(event) {
            var delta = 0;
            if (!event) /* For IE. */
                    event = window.event;
            if (event.wheelDelta) { /* IE/Opera. */
                    delta = event.wheelDelta/120;
                    if (window.opera)
                            delta = -delta;
            } else if (event.detail) { /** Mozilla case. */
                    delta = -event.detail/3;
            }
            if (delta)
                    this.scrollTable(delta);
            if (event.preventDefault)
                event.preventDefault();
        event.returnValue = false;
    },
    scrollTable: function(delta) {
        if (this.scrollTimeout) clearTimeout(this.scrollTimeout);
        var pixelDelta = delta * (this.rowHeight+4);
        this.scrollbar.scrollTop -= pixelDelta;
    },
    getColLengths: function() {
        var lens = new Array();
        this.fieldMapping = {
            summary: -2,
            firstTime: 0,
            lastTime: 0,
            component: -1,
            count: +3
        }
        this.fieldOffsetTotal = 0;
        for (i=0;i<this.fields.length;i++) {
            var field = this.fields[i];
            var offset = this.fieldMapping[field[0]] || 0;
            lens[lens.length] = field[1] + offset;
        }
        return lens
    },
    refreshWithParams: function(params, offset, url) {
        this.buffer.clear();
        if (offset) this.lastOffset = offset;
        this.url = url || this.url;
        //this.clearFirst = true;
        update(this.lastparams, params);
        this.refreshTable(this.lastOffset);
    },
    query: function(offset) {
        var url = this.url || 'getJSONEventsInfo';
        this.lastOffset = offset;
        var qs = update(this.lastparams, {
            'offset': this.buffer.queryOffset(offset),
            //'fields:list': this.fieldnames,
            'count': this.buffer.querySize(offset), 
            'getTotalCount': 1
        });
        var d = loadJSONDoc(url, qs);
        d.addErrback(function(x) { log("BROKEN! " + x)});
        d.addCallback(
         bind(function(r) {
             result = r; //evalJSON(r.responseText); // For POST
             this.buffer.totalRows = result[1];
             this.setScrollHeight(this.buffer.totalRows*(this.rowHeight+4));
             this.buffer.update(result[0], offset);
             this.lock.release();
         }, this));
    },
    refreshTable: function(offset) {
        this.showLoading();
        var offset = offset || this.lastOffset;
        if (offset + this.numRows > this.buffer.startPos + this.buffer.size ||
                offset < this.buffer.startPos - this.numRows) {
            d = this.lock.acquire();
            d.addCallback(bind(function() {
              this.query(offset);
            }, this));
        };
        popLock = this.lock.acquire();
        popLock.addCallback(bind(function() {
            this.lock.release();
            this.populateTable(this.buffer.getRows(offset, this.numRows));
        }, this));
    },
    getBlankRow: function(indx) {
        var i = String(indx);
        cells = map(function(x) {return TD({
            'class':'cell',
            'id':x[0]+'_'+i}, 
                DIV({'class':'cell_inner'}, null))},
            this.fields);
        return TR({'class':'zengrid_row'}, cells);
    },
    populateRow: function(row, data) {
        var stuffz = getElementsByTagAndClassName('div', 'cell_inner', row)
        for (i=0;i<stuffz.length;i++) {
            stuffz[i].innerHTML = data[i];
            //addElementClass(stuffz[i], data[data.length-1]);
        }

        if (isManager) {
            var cb = INPUT({type:'checkbox',
                style: 'visibility:hidden;'}, null);
            replaceChildNodes(stuffz[0], cb);
        }
    },
    getColgroup: function() {
        var widths = this.getColLengths();
        var cols = map(function(w){
            if (parseFloat(w)<3) w=String(3);
            return createDOM( 'col', {width: w+'%'}, null)
        }, widths);
        colgroup = createDOM('colgroup', {span:widths.length, height:'32px'}, 
            cols);
        return colgroup;
    },
    connectHeaders: function(cells) {
        for(i=isManager?1:0;i<cells.length;i++) { 
            setStyle(cells[i], {'cursor':'pointer'});
            connect(cells[i], 'onclick',
                bind(function(e) {
                    var cell = e.src();
                    var f = cell.getElementsByTagName('div')[0].innerHTML;
                    this.refreshWithParams({'orderby': f });
                }, this)
            );
        }
    },
    refreshWidths: function() {
        var widths = this.getColLengths();
        var parentwidth = getElementDimensions(this.viewport).w;
        this.abswidths = new Array();
        for (i=0;i<widths.length;i++) {
            var p = widths[i];
            var myw = parseInt(parentwidth*(p/100));
            this.abswidths[i] = myw;
        }
    },
    refreshFields: function() {
        var updateColumns = bind(function() {
            var numcols = this.fields.length;
            var fields = map(function(x){return x[0]}, this.fields);
            this.refreshWidths();

            this.colgroup = swapDOM(this.colgroup, this.getColgroup());
            this.headcolgroup = swapDOM(this.headcolgroup, this.getColgroup());

            var headerrow = this.getBlankRow('head');
            replaceChildNodes(this.headers.getElementsByTagName('tbody')[0],
                headerrow);
            this.populateRow(headerrow, fields);
            cells = this.headers.getElementsByTagName('td');
            this.connectHeaders(cells);
            this.setTableNumRows(this.numRows);
            this.lock.release();
        }, this);
        fieldparams = {};
        if (this.isHistory) fieldparams['history'] = 1;
        var x = loadJSONDoc('getJSONFields', fieldparams);
        x.addCallback(bind(function(r){
            this.fields=r;
            if (isManager) this.fields = concat([['&nbsp;','']], this.fields);
            updateColumns();
        }, this));
    },
    clearTable: function() {
        table = this.zgtable;
        var cells = getElementsByTagAndClassName('div', 'cell_inner', table);
        for (i=0;(cell=cells[i]);i++){
            replaceChildNodes(cell, null);
        }
    },
    setTableNumRows: function(numrows) {
        this.rowEls = map(this.getBlankRow, range(numrows));
        replaceChildNodes(this.output, this.rowEls);
        setElementDimensions(this.viewport,
            {h:parseInt(numrows*(this.rowHeight+4))}
        );
        var scrollHeight = parseInt(numrows * (this.rowHeight+4));
        if (scrollHeight<=getElementDimensions(this.zgtable).h) {
            setStyle(this.scrollbar, {'display':'none'});
        } else {
            setElementDimensions(this.scrollbar, {h:scrollHeight});
        }
    },
    populateTable: function(data) {
        var tableLength = data.length > this.numRows ? 
            this.numRows : data.length;
        if (tableLength != this.rowEls.length){ 
            this.clearTable();
            this.setTableNumRows(tableLength);
        }
        rows = this.rowEls;
        disconnectAllTo(this.markAsChecked);
        for (i=0;i<rows.length&&i<data.length;i++) {
            var mydata = data[i];
            var evid = mydata[mydata.length-2];
            var chkboxparams = {type:'checkbox', name:'evids:list',
                                value:evid};
            if (this.checkedArray[evid]) chkboxparams.checked=true;
                var chkbox = INPUT(chkboxparams, null);
            var yo = rows[i].getElementsByTagName('td');
            var divs = getElementsByTagAndClassName('div','cell_inner', rows[i]);
            var firstcol = yo[0];
            if (isManager) {
                mydata = concat([''],mydata);
                replaceChildNodes(divs[0], chkbox);
                setElementClass(firstcol, 'cell ' + mydata[mydata.length-1])
                connect(chkbox, 'onclick', this.markAsChecked);
            }
            for (j=isManager?1:0;j<yo.length;j++) {
                var cellwidth = this.abswidths[j]
                switch (this.fields[j][0]) {
                    case 'firstTime':
                    case 'lastTime':
                        replaceChildNodes(divs[j], isoTimestamp(mydata[j]));
                    default:
                        divs[j].innerHTML = mydata[j];
                }
                divs[j].title = this.abswidths[j];
                var newClass = 'cell ' + mydata[mydata.length-1];
                if (yo[j].className!=newClass)
                    setElementClass(yo[j], newClass)
            }

        }
        connectCheckboxListeners();
        this.killLoading();
    },
    getTotalRows: function() {
        cb = bind(function(r) {
            this.buffer.totalRows = r;
            this.setScrollHeight(this.buffer.totalRows*(this.rowHeight+4));
            this.lock.release();
        }, this);
        d = loadJSONDoc('getEventCount');
        d.addCallback(cb);
    },
    getHeaderWidths: function() {
        var myws = new Array();
        for (i=0;i<this.fields.length;i++) {
            var width = this.fields[i][0].length * this.fontProportion * 12;
            myws[myws.length] = width;
        }
        return myws
    },
    buildHTML: function() {
        var getId = function(thing) { 
            return "zg_" + thing + "_" + this.gridId }
        getId = bind(getId, this);
        this.scrollbar = DIV(
            {id : getId('scroll')},
            DIV({style: 'height:1000px;'}, null)
        );
        this.output = TBODY( {id: getId('output')}, null);
        this.headcolgroup = createDOM('colgroup', null, null);
        this.colgroup = createDOM( 'colgroup', 
            {style: 'height:'+this.rowHeight+'px'}, null );
        this.zgtable = TABLE( {id: getId('table'),
            cellspacing:0, cellpadding:0}, [
            THEAD(null, null),
            this.colgroup,
            this.output,
            TFOOT(null, null)
        ]);
        this.viewport = DIV( {id: getId('viewport')}, this.zgtable );
        this.headers = TABLE( {id: getId('headers'), class:"zg_headers",
            cellspacing:0, cellpadding:0}, [
            this.headcolgroup,
            TBODY(null, null)
        ]);
        this.innercont = DIV( {id:getId('innercont')}, 
            [this.viewport, this.scrollbar]);
        setStyle(this.zgtable, {
            'width': '100%',
            'border': 'medium none',
            'background-color':'#888',
            'padding':'0',
            'margin':'0'
        });
        setStyle(this.headers, {
            'width':'98%'
        });
        setStyle(this.innercont, {
            'width':'100%'
        });
        setStyle(this.viewport, {
            'width':'98%',
            'height':(this.rowHeight+4)*(this.numRows)+'px',
            'overflow':'hidden',
            'float':'left',
            'border':'1px solid black',
            'border-right':'medium none'
        });
        addElementClass(this.viewport, 'leftfloat');
        setStyle(this.scrollbar, 
            { 'border': '1px solid black',
              'border-left': 'medium none',
              'overflow': 'auto',
              'position': 'relative',
              'left': '-3px',
              'width': '19px',
              'height': (this.rowHeight+4)*(this.numRows)+'px' 
        });
        var scrollHeight = this.buffer.totalRows * (this.rowHeight+4);
        this.setScrollHeight(scrollHeight);
        appendChildNodes(this.container, this.headers, this.innercont);
    },

    setScrollHeight: function(scrlheight) {
        setStyle(this.scrollbar, {'display':'block'});
        setStyle(this.scrollbar.getElementsByTagName('div')[0],
            {'height':String(parseInt(scrlheight)) + 'px'}
        );
    },
    scrollToPixel: function(pixel) {
        this.lastPixelOffset = this.lastPixelOffset || 0;
        //var diff = (pixel-this.lastPixelOffset) % (this.rowHeight+4);
        //if (diff) {
            //pixel += diff;
        //}
        var newOffset = Math.round(pixel/(this.rowHeight+4));
        this.refreshTable(newOffset);
        this.scrollbar.scrollTop = pixel;
        this.lastPixelOffset = pixel;
    },
    handleScroll: function() {
        this.showLoading();
        clearTimeout(this.scrollTimeout);
        this.nextScrollPosition = this.scrollbar.scrollTop || 0;
        if (this.nextScrollPosition==0) this.scrollToPixel(this.nextScrollPosition);
        this.scrollTimeout = setTimeout (
            bind(function() {
                this.scrollToPixel(this.nextScrollPosition)
            }, this), 50);
    },
    refreshFromFormElement: function(e) {
        node = e.src();
        id = node.id;
        params = {};
        if (!!node.value) params[id] = node.value;
        this.refreshWithParams(params)
    },
    LSTimeout: null,
    doEventLivesearch: function(e) {
        var filters = e.src().value;
        switch (e.key().string) {
            case 'KEY_TAB':
            case 'KEY_ENTER':
                clearTimeout(this.LSTimeout);
                this.refreshWithParams({filter:filters});
                return;
            case 'KEY_ESCAPE':
            case 'KEY_ARROW_LEFT':
            case 'KEY_ARROW_RIGHT':
            case 'KEY_HOME':
            case 'KEY_END':
            case 'KEY_SHIFT':
            case 'KEY_ARROW_UP':
            case 'KEY_ARROW_DOWN':
                return;
        }
        clearTimeout(this.LSTimeout);
        this.LSTimeout = setTimeout(
        bind(
        function () {
            this.refreshWithParams({filter:filters})
        }, this),
        500);
    },
    markAsChecked: function(e) {
        var node = e.src();
        this.checkedArray[node.value] = node.checked;
    },
    showLoading: function() {
        clearTimeout(this.isLoading);
        this.isLoading = setTimeout( bind(function() {
            this.loadingbox.show();
        }, this), 500);
    },
    killLoading: function() {
        clearTimeout(this.isLoading);
        if (this.loadingbox) {
            this.loadingbox.hide();
        }
    }
}

log('ZenGrid javascript loaded.');
