
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
        appendChildNodes($('frame'), this.framework);
        this.show();

    },
    getViewportCenter: function() {
        var dims = getViewportDimensions();
        var pos = getViewportPosition();
        return new Coordinates((dims.w/2)+pos.x, (dims.h/2)+pos.y);
    },
    show: function(msg) {
        if (msg) $('zengridload_content').innerHTML = msg;
        var p = this.getViewportCenter();
        var d = getElementDimensions(this.framework);
        var pos = new Coordinates(p.x-(d.w/2),p.y-(d.h/2));
        setElementPosition(this.framework, pos);
        showElement(this.framework);
    },
    hide: function() {
        hideElement(this.framework);
    }
}
var DeviceZenGridBuffer = Class.create();

DeviceZenGridBuffer.prototype = {
    __init__: function(url) {
        this.startPos = 0;
        this.size = 0;
        this.rows = new Array();
        this.updating = false;
        this.grid = null;
        this.maxQuery = 50;
        this.totalRows = 0;
        this.numRows = 0;
        this.numCols = 0;
        this.pageSize = 10;
        this.bufferSize = 5; 
        this.marginFactor = 0.2; 
        bindMethods(this);
    },
    tolerance: function() {
        return parseInt(this.bufferSize * this.pageSize * this.marginFactor);
    },
    endPos: function() {return this.startPos + this.rows.length;},
    querySize: function(newOffset) {
        var newSize = 0;
        if (newOffset >= this.startPos) { //appending
            var endQueryOffset = this.maxQuery + this.grid.lastOffset;
            newSize = endQueryOffset - newOffset;
            if(newOffset==0 && newSize < this.maxQuery)
                newSize = this.maxQuery;
        } else { // prepending
            newSize = Math.min(this.startPos - newOffset, this.maxQuery);
        }
        return newSize;
    },
    queryOffset: function(offset) {
        var newOffset = offset;
        var goingup = Math.abs(this.startPos - this.grid.lastOffset);
        var goingdown = Math.abs(this.grid.lastOffset - this.endPos());
        var reverse = goingup < goingdown;
        if (offset > this.startPos && !reverse){ 
            newOffset = Math.max(offset, this.endPos()); //appending
        }
        else if (offset > this.startPos && reverse) {
            newOffset = Math.max(0, 
                offset - this.maxQuery + (2*this.tolerance()));
            if (offset-newOffset-this.maxQuery<this.tolerance()) {
                newOffset += this.tolerance()
            }
            if (offset-newOffset-this.maxQuery<this.tolerance()) {
                newOffset += (2*this.tolerance());
            }
        }
        else if (offset + this.maxQuery >= this.startPos) {
            newOffset = Math.max(this.startPos - this.maxQuery, 0); //prepending

            if (offset-newOffset-this.maxQuery<this.tolerance()) {
                newOffset = Math.min(offset, newOffset + (2*this.tolerance()));
            }
        }
        return newOffset;
    },
    getRows: function(start, count) {
        var bPos = start - this.startPos;
        var ePos = Math.min(bPos+count, this.size);
        var results = new Array();
        for (var i=bPos; i<ePos; i++)
            results.push(this.rows[i]);
        return results;
    },
    isInRange: function(start) {
        var lastRow = Math.min(start + this.pageSize);
        return (start >= this.startPos)&&(lastRow<=this.endPos())&&(this.size!=0);
    },
    update: function(response, start) {
        var newRows = response;
        if (newRows==null) return;
        this.rcvdRows = newRows.length;
        if (this.rows.length==0) { // initial load
            this.rows = newRows;
            this.startPos = start;
        } else if (start > this.startPos) { // appending
            if (this.startPos + this.rows.length < start) {
                this.rows = newRows;
                this.startPos = start;
            } else {
                this.rows = this.rows.concat( newRows.slice(0, newRows.length));
                if (this.rows.length > this.maxQuery) {
                    var fullSize = this.rows.length;
                    this.rows = this.rows.slice(
                        this.rows.length - this.maxQuery, this.rows.length
                    );
                    this.startPos = this.startPos + (fullSize - this.rows.length);
                }
            }
        } else { //prepending
            if (start + newRows.length < this.startPos) {
                this.rows = newRows;
            } else {
                this.rows = newRows.slice(0, this.startPos).concat(this.rows);
                if (this.maxQuery && this.rows.length > this.maxQuery)
                    this.rows = this.rows.slice(0, this.maxQuery)
            }
            this.startPos = start;
        }
        this.size = this.rows.length;
    },
    clear: function() {
        this.rows = new Array();
        this.startPos = 0;
        this.size = 0;
    }
}


var DeviceZenGrid = Class.create();

DeviceZenGrid.prototype = {
    __init__: function(container, url, gridId, buffer, absurl) {
        bindMethods(this);
        this.absurl = absurl;
        this.container = $(container);
        this.gridId = gridId;
        this.buffer = buffer;
        this.buffer.grid = this;
        this.numRows = 10;
        this.rowHeight = 26;
        this.checkedArray = new Array();
        this.url = this.absurl + '/' + url;
        this.lastparams = {};
        this.fields = [];
        this.lastOffset = 0;
        this.lastPixelOffset = this.lastPixelOffset || 0;
        var isMSIE//@cc_on=1;
        this.rowSizePlus = this.rowHeight+(isMSIE?5:3);
        this.buildHTML();
        this.selectstatus = 'none';
        this.clearFirst = false;
        this.lock = new DeferredLock();
        this.scrollTimeout = null;
        this.loadingbox = new ZenGridLoadingMsg('Loading...');
        fieldlock = this.lock.acquire();
        fieldlock.addCallback(this.refreshFields);
        updatelock = this.lock.acquire();
        updatelock.addCallback(bind(function(r){
            this.resizeTable();
            if (this.lock.locked) this.lock.release();
        }, this));
        statuslock = this.lock.acquire();
        statuslock.addCallback(bind(function(r){
            if (this.lock.locked) this.lock.release();
        }, this));
        this.addMouseWheelListening();
        connect(this.scrollbar, 'onscroll', this.handleScroll);
        connect(currentWindow(), 'onresize', this.resizeTable);
    },
    turnRefreshOn: function() {
        var time = $('refreshRate').value;
        this.refreshMgr = new RefreshManager(time, this.refresh);
        var button = $('refreshButton');
        setStyle(button, 
            {'background-image':'url(img/refresh_off.png)'});
        button.onclick = this.turnRefreshOff;
        button.blur();
    },
    turnRefreshOff: function() {
        var button = $('refreshButton');
        this.refreshMgr.cancelRefresh();
        delete this.refreshMgr;
        setStyle(button,
            {'background-image':'url(img/refresh_on.png)'});
        button.onclick = this.turnRefreshOn;
        button.blur();
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
        this.fieldOffsetTotal = 0;
        for (i=0;i<this.fields.length;i++) {
            var field = this.fields[i];
            var offset = 0;
            lens[lens.length] = field[1] + offset;
        }
        return lens
    },
    refreshWithParams: function(params, offset, url) {
        this.buffer.clear();
        if (offset) this.lastOffset = offset;
        this.url = url || this.url;
        update(this.lastparams, params);
        this.refreshTable(this.lastOffset);
    },
    refresh: function() {
        bufOffset = this.buffer.startPos;
        qs = update(this.lastparams, {
                'offset':this.buffer.startPos,
                'count':this.buffer.size });
        var d = loadJSONDoc(this.url, qs);
        d.addErrback(bind(function(x) { 
            callLater(5, bind(function(){
            alert('Cannot communicate with the server!');
            this.killLoading()}, this))
        }, this));
        d.addCallback(
            bind(function(r) {
                result = r; 
                this.buffer.totalRows = result[1];
                this.setScrollHeight(this.rowToPixel(this.buffer.totalRows));
                this.buffer.clear();
                this.buffer.update(result[0], bufOffset);
                this.updateStatusBar(this.lastOffset);
                this.populateTable(this.buffer.getRows(this.lastOffset, this.numRows));
            }, this)
        );
    },
    query: function(offset) {
        var url = this.url || 'getJSONDeviceInfo';
        this.lastOffset = offset;
        bufOffset = this.buffer.queryOffset(offset);
        bufSize = this.buffer.querySize(bufOffset);
        var qs = update(this.lastparams, {
            'offset': bufOffset,
            'count': bufSize
        });
        var d = loadJSONDoc(url, qs);
        d.addErrback(bind(function(x) { 
            callLater(5, bind(function(){
            alert('Cannot communicate with the server!');
            this.killLoading()}, this))
        }, this));
        d.addCallback(
         bind(function(r) {
             result = r; 
             this.buffer.totalRows = result[1];
             this.setScrollHeight(this.rowToPixel(this.buffer.totalRows));
             this.buffer.update(result[0], bufOffset);
             if (this.lock.locked) this.lock.release();
         }, this));
    },
    refreshTable: function(offset) {
        this.showLoading();
        var lastOffset = this.lastOffset;
        this.lastOffset = offset;
        this.scrollbar.scrollTop = this.rowToPixel(offset);
        var inRange = this.buffer.isInRange(offset);
        if (inRange) {
            this.populateTable(this.buffer.getRows(offset, this.numRows));
            if (offset > lastOffset) {
                if (offset+this.buffer.pageSize < 
                    this.buffer.endPos()-this.buffer.tolerance()) return;
            } else if (offset < lastOffset) {
                if (offset > this.buffer.startPos + this.buffer.tolerance()) 
                    return;
                if (this.buffer.startPos==0) return;
            } else return;
        }
        if (offset >= this.buffer.totalRows && this.buffer.rcvdRows) return;
        d = this.lock.acquire();
        d.addCallback(bind(function() {
          this.query(offset);
        }, this));
        popLock = this.lock.acquire();
        popLock.addCallback(bind(function() {
            if (this.lock.locked) this.lock.release();
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
        setNodeAttribute(cells[cells.length-1], 'nowrap', 'true');
        return TR({'class':'devzengrid_rows'}, cells);
    },
    populateRow: function(row, data) {
        var stuffz = row.getElementsByTagName('div')
        for (i=0;i<stuffz.length;i++) {
            stuffz[i].innerHTML = data[i];
        }
        if (isManager) {
            var cb = '<input type="checkbox" style="visibility:hidden"/>';
            stuffz[0].innerHTML = cb;
        }
        setStyle(stuffz[0], {'width':'20px'});
    },
    getColgroup: function() {
        var widths = this.getColLengths();
        var cols = map(function(w){
            if (parseFloat(w)<3) w=String(3);
            return createDOM( 'col', {width: w+'%'}, null)
        }, widths);
        updateNodeAttributes(cols[0], {width:'0*'});
        colgroup = createDOM('colgroup', {span:widths.length, height:'25px'}, 
            cols);
        return colgroup;
    },
    connectHeaders: function(cells) {
        for(i=isManager?1:0;i<cells.length;i++) { 
            setStyle(cells[i], {'cursor':'pointer'});
            connect(cells[i], 'onclick', this.toggleSortOrder);
        }
    },
    toggleSortOrder: function(e) {
        var fieldmap = {
            'Device Id':'id',
            'IP':'getDeviceIp',
            'Class':'getDeviceClassPath',
            'Prod State':'getProdState',
            'Event Summary':'',
            'Locks':''
        }
        var cell = e.src();
        var f = fieldmap[cell.getElementsByTagName('div')[0].innerHTML];
        var headcells = this.headers.getElementsByTagName('td');
        var clearcell = function(cell){setStyle(cell,{'background':null,'color':null})}
        map(clearcell, headcells);
        if (f) {
        if (this.lastparams['orderby']==f) {
            switch(this.lastparams['orderdir']) {
                case ('asc'):
                    setStyle(cell, {
                        'background':'#888 url(img/arrow.d.gif) right no-repeat',
                        'color':'white'
                    });
                    this.refreshWithParams({'orderby':f, 'orderdir':'desc'});
                    return;
                case ('desc'):
                    clearcell(cell);
                    this.refreshWithParams({'orderby':'id','orderdir':'asc'});
                    return;
            }
        } else {
            setStyle(cell, {
                'background':'#888 url(img/arrow.u.gif) right no-repeat',
                'color':'white'
            });
            this.refreshWithParams({'orderby':f , 'orderdir':'asc'});
        }
        }

    },
    refreshWidths: function() {
        var widths = this.getColLengths();
        log(widths);
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
            if (this.lock.locked) this.lock.release();
        }, this);
        r = [['Device Id',20.0],['IP',16.0],['Class',20.0],
             ['Prod State',16.0],['Event Summary',14.0],['Locks',10.0]]
        this.fields=r;
        if (isManager) this.fields = concat([['&nbsp;','']], this.fields);
        updateColumns();
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
        var myoffset = numrows*(32-this.rowHeight);
        if (scrollHeight <= 0) 
            setElementDimensions(this.scrollbar, {h:0});
        else if
            (scrollHeight<=getElementDimensions(this.zgtable).h-myoffset-2) {
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
            setElementClass(rows[i], (this.lastOffset+i)%2?'odd':'even')
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
                setStyle(divs[0], {'width':'21px'});
                connect($(evid), 'onclick', this.markAsChecked);
            }
            for (j=isManager?1:0;j<yo.length;j++) {
                var cellwidth = this.abswidths[j]
                divs[j].innerHTML = unescape(mydata[j]);
                yo[j].title = scrapeText(divs[j]);
            }

        }
        this.killLoading();
        connectCheckboxListeners();
    },
    getTotalRows: function() {
        cb = bind(function(r) {
            this.buffer.totalRows = r;
            this.setScrollHeight(this.rowToPixel(this.buffer.totalRows));
            if (this.lock.locked) this.lock.release();
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
        this.statusBar = DIV( {id:getId('statusbar'), 'class':'zg_statusbar'}, 
            SPAN({id:'currentRows'}, String(0+1 +'-'+ parseInt(parseInt(0)+parseInt(this.numRows)) +  ' of ' + this.buffer.totalRows)),
        [   'Select:  ',
            UL(null,
            [
                LI({'id':'setSelectAll'}, 'All'),
                LI({'id':'setSelectNone'}, 'None')
            ])
        ]
        );
        this.headers = TABLE( {id: getId('headers'), 'class':"zg_headers",
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
            'border-right':'medium none',
            'border-bottom':'medium none'
        });
        addElementClass(this.viewport, 'leftfloat');
        setStyle(this.scrollbar, 
            { 'border-left': 'medium none',
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
    },

    setScrollHeight: function(scrlheight) {
        setStyle(this.scrollbar, {'display':'block'});
        setStyle(this.scrollbar.getElementsByTagName('div')[0],
            {'height':String(parseInt(scrlheight)) + 'px'}
        );
    },
    rowToPixel: function(row) {
        return row * (this.rowSizePlus);
    },
    pixelToRow: function(pixel) {
        var prow = parseInt(pixel/(this.rowSizePlus));
        return Math.max(0, prow);
    },
    scrollToPixel: function(pixel) {
        var diff = this.lastPixelOffset-pixel;
        if (diff==0.00) return;
        var sign = Math.abs(diff)/diff;
        pixel = sign<0?
        Math.ceil(pixel/(this.rowSizePlus))*(this.rowSizePlus):
        Math.floor(pixel/(this.rowSizePlus))*(this.rowSizePlus);
        var newOffset = this.pixelToRow(pixel);
        this.updateStatusBar(newOffset);
        if (newOffset==0||newOffset==this.buffer.totalRows-this.numRows) 
            this.refreshTable(newOffset);
        clearTimeout(this.scrollTimeout);
        this.scrollTimeout = setTimeout (
            bind(function() {
                this.refreshTable(newOffset);
            }, this), 100);
        this.lastPixelOffset = pixel;
    },
    handleScroll: function() {
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
                clearTimeout(this.LSTimeout);
                this.refreshWithParams({filter:filters});
                return;
            case 'KEY_ENTER':
            e.preventDefault()
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
        this.checkedArray[node.value] = node.checked?'checked':'blank';
    },
    showLoading: function() {
        if (this.isLoading) clearTimeout(this.isLoading);
        this.isLoading = setTimeout( bind(function() {
            this.loadingbox.show();
        }, this), 500);
    },
    killLoading: function() {
        if (this.isLoading) clearTimeout(this.isLoading);
        this.loadingbox.hide();
    },
    resizeTable: function() {
        var maxTableBottom = getViewportDimensions().h +
            getViewportPosition().y - 20;
        var curTableBottom = 
            Math.max(0,
                getElementDimensions(this.viewport).h +
                getElementPosition(this.viewport).y);
        var diff = maxTableBottom - curTableBottom;
        var rowdiff = Math.floor(diff/this.rowSizePlus);
        if (rowdiff==0 && this.buffer.totalRows!=0) return;
        this.numRows = this.buffer.pageSize = Math.max(1, this.numRows + rowdiff);
        this.setTableNumRows( Math.min( this.numRows, this.buffer.totalRows));
        this.refreshTable(this.lastOffset);
        this.updateStatusBar(this.lastOffset);
    },
    resizeColumn: function(index, fromindex, pixeldiff) {
        var cols = this.colgroup.getElementsByTagName('col');
        var hcols = this.headcolgroup.getElementsByTagName('col');
        var oldint = parseFloat(cols[index].width);
        var parentwidth = getElementDimensions(this.viewport).w;
        var old = (oldint/100.00) * parentwidth;
        var neww = (old + pixeldiff)/parentwidth * 100.00;
        var tofield = this.fields[index][0];
        var toval = this.fieldMapping[tofield];
        var fromfield = this.fields[fromindex][0];
        var fromval = this.fieldMapping[fromfield];
        neww = oldint-neww;
        if (toval-neww<0) neww=toval;
        else if (fromval+neww<0) neww=-fromval;
        this.fieldMapping[tofield] = Math.max(toval-neww, 0);
        this.fieldMapping[fromfield] = Math.max(fromval+neww, 0);
        this.colgroup = swapDOM(this.colgroup, this.getColgroup());
        this.headcolgroup = swapDOM(this.headcolgroup, this.getColgroup());
        //this.refreshTable(this.lastOffset);
    },
    setDeviceBatchProps: function(method, extraarg) {
        log(method, extraarg);
        url = this.absurl + '/setDeviceBatchProps';
        var selectstatus = this.selectstatus;
        var goodevids = [];
        var badevids = [];
        for (var evid in this.checkedArray) {
            if (this.checkedArray[evid]=='checked') goodevids.push(evid);
            else badevids.push(evid);
        }
        qs = {
                'selectstatus':selectstatus, 
                'goodevids':goodevids,
                'badevids':badevids,
                'method':method,
                'extraarg':extraarg
             }
        qs = update(qs, this.lastparams);
        $('dialog').hide();
        this.showLoading();
        d = doXHR(url, {queryString:qs}); 
        d.addCallback(bind(
            function(r) { 
                this.buffer.clear();
                this.refreshTable(this.lastOffset);
                this.setSelectNone();
                showMessage(r.responseText);
            }, this));
    }
}

log('ZenGrid javascript loaded.');

