
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
            'z-index':'11000'
        });
        setStyle($('zengridload_content'), {
            'font-weight':'bold',
            'font-size':'2em',
            'text-align':'center'

        });

    },
    show: function(center) {
        setStyle(this.framework, {'display':'block'});
    },
    hide: function() {
        setStyle(this.framework, {'display':'none'});
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
        this.numRows = 10;
        this.rowHeight = 32;
        this.checkedArray = new Array();
        this.url = url;
        this.lastparams = {};
        this.fields = [];
        this.lastOffset = 0;
        this.lastPixelOffset = this.lastPixelOffset || 0;
        this.buildHTML();
        this.selectstatus = 'none';
        this.clearFirst = false;
        this.lock = new DeferredLock();
        this.scrollTimeout = null;
        this.loadingbox = new ZenGridLoadingMsg('Loading...');
        this.showLoading();
        fieldlock = this.lock.acquire();
        fieldlock.addCallback(this.refreshFields);
        updatelock = this.lock.acquire();
        updatelock.addCallback(bind(function(r){
            this.refreshTable(this.lastOffset);
            this.lock.release();
        }, this));
        statuslock = this.lock.acquire();
        statuslock.addCallback(bind(function(r){
            //this.updateStatusBar(this.lastOffset);
            this.lock.release();
        }, this));
        this.addMouseWheelListening();
        connect(this.scrollbar, 'onscroll', this.handleScroll);
    },
    setSelectNone: function() {
        this.checkedArray = new Array();
        var cbs = this.viewport.getElementsByTagName('input');
        for (i=0;i<cbs.length;i++) {
            cbs[i].checked=null;
        }
        this.selectstatus = 'none';
    },
    setSelectAll: function() {
        this.checkedArray = new Array();
        var cbs = this.viewport.getElementsByTagName('input');
        for (i=0;i<cbs.length;i++) {
            cbs[i].checked=true;
        }
        this.selectstatus = 'all';
    },
    setSelectAcked: function() {
        this.checkedArray = new Array();
        var cbs = this.viewport.getElementsByTagName('input');
        var rows = this.zgtable.getElementsByTagName('tr');
        for (i=0;i<cbs.length;i++) {
            rowclass = rows[i].className;
            cbs[i].checked=null;
            if (rowclass.match('acked')) cbs[i].checked=true;
        }
        this.selectstatus = 'acked';
    },
    setSelectUnacked: function() {
        this.checkedArray = new Array();
        var cbs = this.viewport.getElementsByTagName('input');
        for (i=0;i<cbs.length;i++) {
            rowclass = rows[i].className;
            cbs[i].checked=null;
            if (rowclass.match('noack')) cbs[i].checked=true;
        }
        this.selectstatus = 'unacked';
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
        var pixelDelta = this.rowToPixel(delta);
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
             this.setScrollHeight(this.rowToPixel(this.buffer.totalRows));
             this.buffer.update(result[0], offset);
             this.lock.release();
         }, this));
    },
    refreshTable: function(offset) {
        this.showLoading();
        var offset = offset || this.lastOffset;
        this.scrollbar.scrollTop = this.rowToPixel(offset);
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
            this.updateStatusBar(offset);
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
        var stuffz = row.getElementsByTagName('div')
        for (i=0;i<stuffz.length-1;i++) {
            stuffz[i].innerHTML = data[i];
        }
        setElementClass(stuffz[stuffz.length-1], 'event_detail');    

        if (isManager) {
            var cb = '<input type="checkbox" style="visibility:hidden"/>';
            stuffz[0].innerHTML = cb;
        }
        setStyle(stuffz[0], {'width':'20px'});
        setStyle(stuffz[stuffz.length-1], {'width':'32px'});
    },
    getColgroup: function() {
        var widths = this.getColLengths();
        var cols = map(function(w){
            if (parseFloat(w)<3) w=String(3);
            return createDOM( 'col', {width: w+'%'}, null)
        }, widths);
        cols[0].width='0*';
        cols[cols.length-1].width='32';
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
            this.fields=concat(r,[['&nbsp;','']]);
            if (isManager) this.fields = concat([['&nbsp;','']], this.fields);
            updateColumns();
        }, this));
    },
    clearTable: function() {
        table = this.zgtable;
        var cells = getElementsByTagAndClassName('div', 'cell_inner', table);
        for (i=0;(cell=cells[i]);i++){
            cell.innerHTML='';
        }
    },
    setTableNumRows: function(numrows) {
        this.rowEls = map(this.getBlankRow, range(numrows));
        replaceChildNodes(this.output, this.rowEls);
        setElementDimensions(this.viewport,
            {h:parseInt(this.rowToPixel(numrows))}
        );
        var scrollHeight = parseInt(this.rowToPixel(numrows));
        if (scrollHeight<=getElementDimensions(this.zgtable).h) {
            setStyle(this.scrollbar, {'display':'none'});
        } else {
            setElementDimensions(this.scrollbar, {h:scrollHeight});
        }
    },
    shouldBeChecked: function(evid, klass) {
        if (this.checkedArray[evid]=='checked') 
            return true;
        if (this.checkedArray[evid]=='blank')
            return false;
        switch (this.selectstatus) {
            case 'none': return false;
            case 'all': return true;
            case 'acked':
                return !!klass.match('acked');
            case 'unacked':
                return !!klass.match('noack');
        }
        return false;
    },
    populateTable: function(data) {
        var zem = this.isHistory?'/zport/dmd/ZenEventHistory':
            '/zport/dmd/ZenEventManager';
        var tableLength = data.length > this.numRows ? 
            this.numRows : data.length;
        if (tableLength != this.rowEls.length){ 
            //this.clearTable();
            this.setTableNumRows(tableLength);
        }
        rows = this.rowEls;
        disconnectAllTo(this.markAsChecked);
        for (i=0;i<rows.length&&i<data.length;i++) {
            var mydata = data[i];
            setElementClass(rows[i], mydata[mydata.length-1])
            var evid = mydata[mydata.length-2];
            var chkbox = '<input type="checkbox" name="evids:list" ';
            if (this.shouldBeChecked(evid, mydata[mydata.length-1])) 
                chkbox+='checked ';
            chkbox += 'value="'+evid+'" id="'+evid+'"/>';
            var yo = rows[i].getElementsByTagName('td');
            var divs = rows[i].getElementsByTagName('div');
            var firstcol = yo[0];
            if (isManager) {
                mydata = concat([''],mydata);
                divs[0].innerHTML = chkbox;
                setStyle(divs[0], {'width':'20px'});
                //setElementClass(firstcol, 'cell ' + mydata[mydata.length-1])
                connect($(evid), 'onclick', this.markAsChecked);
            }
            var lastcol = yo[yo.length-1];
            //setElementClass(lastcol, 'cell ' + mydata[mydata.length-1])
            setElementClass(divs[yo.length-1], 'event_detail');    
            disconnectAll(divs[yo.length-1]);
            connect(divs[yo.length-1], 'onclick', function() {
                eventWindow(zem, evid);
            });
            divs[yo.length-1].title = "View detailed information" + 
                " about this event."
            for (j=isManager?1:0;j<yo.length-1;j++) {
                var cellwidth = this.abswidths[j]
                divs[j].innerHTML = mydata[j];
                yo[j].title = mydata[j];
                //var newClass = 'cell ' + mydata[mydata.length-1];
                //if (yo[j].className!=newClass)
                    //setElementClass(yo[j], newClass)
            }

        }
        connectCheckboxListeners();
        this.killLoading();
    },
    getTotalRows: function() {
        cb = bind(function(r) {
            this.buffer.totalRows = r;
            this.setScrollHeight(this.rowToPixel(this.buffer.totalRows));
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
        this.statusBar = DIV( {id:getId('statusbar'), class:'zg_statusbar'}, 
            SPAN({id:'currentRows'}, String(0+1 + '-' +
            parseInt(parseInt(0)+parseInt(this.numRows)) + 
            ' of ' + this.buffer.totalRows)),
        [   'Select:  ',
            UL(null,
            [
                LI({'id':'setSelectNone'}, 'None'),
                LI({'id':'setSelectAll'}, 'All'),
                LI({'id':'setSelectAcked'}, 'Acknowledged'),
                LI({'id':'setSelectUnacked'}, 'Unacknowledged')
            ])
        ]
        );
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
            'height':this.rowToPixel(this.numRows)+'px',
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
              'z-index':'300',
              'position': 'relative',
              'left': '-3px',
              'width': '19px',
              'height': this.rowToPixel(this.numRows)+'px' 
        });
        var scrollHeight = this.rowToPixel(this.buffer.totalRows);
        this.setScrollHeight(scrollHeight);
        appendChildNodes(this.container, this.statusBar, this.headers, this.innercont);
        connect('setSelectNone', 'onclick', this.setSelectNone);
        connect('setSelectAll', 'onclick', this.setSelectAll);
        connect('setSelectAcked', 'onclick', this.setSelectAcked);
        connect('setSelectUnacked', 'onclick', this.setSelectUnacked);
    },

    setScrollHeight: function(scrlheight) {
        setStyle(this.scrollbar, {'display':'block'});
        setStyle(this.scrollbar.getElementsByTagName('div')[0],
            {'height':String(parseInt(scrlheight)) + 'px'}
        );
    },
    rowToPixel: function(row) {
        return row * (this.rowHeight+4);
    },
    pixelToRow: function(pixel) {
        var prow = parseInt(pixel/(this.rowHeight+4));
        return Math.max(0, prow);
    },
    scrollToPixel: function(pixel) {
        var diff = this.lastPixelOffset-pixel;
        if (diff==0.00) return;
        var sign = Math.abs(diff)/diff;
        pixel = sign<0?
        Math.ceil(pixel/(this.rowHeight+4))*(this.rowHeight+4):
        Math.floor(pixel/(this.rowHeight+4))*(this.rowHeight+4);
        var newOffset = this.pixelToRow(pixel);
        this.updateStatusBar(newOffset);
        if (newOffset==0) this.refreshTable(newOffset);
        clearTimeout(this.scrollTimeout);
        this.scrollTimeout = setTimeout (
            bind(function() {
                this.refreshTable(newOffset);
            }, this), 100);
        this.lastPixelOffset = pixel;
    },
    handleScroll: function() {
        this.showLoading();
        this.scrollToPixel(this.scrollbar.scrollTop||0)
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
    updateStatusBar: function(rownum) {
        $('currentRows').innerHTML = rownum+1 + '-' +
            parseInt(parseInt(rownum)+
            Math.min(parseInt(this.numRows), parseInt(this.buffer.totalRows))
        ) + ' of ' + this.buffer.totalRows;
    },
    markAsChecked: function(e) {
        var node = e.src();

        this.checkedArray[node.value] = node.checked?
            'checked':'blank'
    },
    getViewportCenter: function() {
        var dims = getElementDimensions(this.viewport);
        var pos = getElementPosition(this.viewport);
        return {x:(dims.w/2)+pos.x, y:(dims.h/2)+pos.y}
    },
    showLoading: function() {
        clearTimeout(this.isLoading);
        this.isLoading = setTimeout( bind(function() {
            var p = this.getViewportCenter();
            var d = getElementDimensions(this.loadingbox);
            var pos = {x:p.x-(d.w/2),y:p.y-(d.h/2)};
            this.loadingbox.style.top = pos.y;
            this.loadingbox.style.left = pos.x;
            this.loadingbox.show(p);
        }, this), 500);
    },
    killLoading: function() {
        clearTimeout(this.isLoading);
        if (this.loadingbox) {
            this.loadingbox.hide();
        }
    },
    resizeColumn: function(index, pixeldiff) {
        var cols = this.colgroup.getElementsByTagName('col');
        var old = cols(index).width;
    }
}

log('ZenGrid javascript loaded.');
