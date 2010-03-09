(function(){ // Local scope
Ext.override(Ext.ux.grid.livegrid.GridView, {
    updateLiveRows: function(index, forceRepaint, forceReload, suspendLoadEvent)
    {
        // Zenoss change beginning
        // Allow us to optionally allow the store load event to fire
        suspendLoadEvent = Ext.isDefined(suspendLoadEvent) ? suspendLoadEvent : true;
        // End change (another below)

        var inRange = this.isInRange(index);


        if (this.isBuffering) {
            if (this.isPrebuffering) {
                if (inRange) {
                    this.replaceLiveRows(index, forceRepaint);
                } else {
                    this.showLoadMask(true);
                }
            }

            this.fireEvent('cursormove', this, index,
                           Math.min(this.ds.totalLength,
                           this.visibleRows-this.rowClipped),
                           this.ds.totalLength);

            this.requestQueue = index;
            return;
        }

        var lastIndex  = this.lastIndex;
        this.lastIndex = index;
        var inRange    = this.isInRange(index);

        var down = false;

        if (inRange && forceReload !== true) {

            // repaint the table's view
            this.replaceLiveRows(index, forceRepaint);
            // has to be called AFTER the rowIndex was recalculated
            this.fireEvent('cursormove', this, index,
                       Math.min(this.ds.totalLength,
                       this.visibleRows-this.rowClipped),
                       this.ds.totalLength);
            // lets decide if we can void this method or stay in here for
            // requesting a buffer update
            if (index > lastIndex) { // scrolling down

                down = true;
                var totalCount = this.ds.totalLength;

                // while scrolling, we have not yet reached the row index
                // that would trigger a re-buffer
                if (index+this.visibleRows+this.nearLimit <= this.ds.bufferRange[1]) {
                    return;
                }

                // If we have already buffered the last range we can ever get
                // by the queried data repository, we don't need to buffer again.
                // This basically means that a re-buffer would only occur again
                // if we are scrolling up.
                if (this.ds.bufferRange[1]+1 >= totalCount) {
                    return;
                }
            } else if (index < lastIndex) { // scrolling up

                down = false;
                // We are scrolling up in the first buffer range we can ever get
                // Re-buffering would only occur upon scrolling down.
                if (this.ds.bufferRange[0] <= 0) {
                    return;
                }

                // if we are scrolling up and we are moving in an acceptable
                // buffer range, lets return.
                if (index - this.nearLimit > this.ds.bufferRange[0]) {
                    return;
                }
            } else {
                return;
            }

            this.isPrebuffering = true;
        }

        // prepare for rebuffering
        this.isBuffering = true;

        var bufferOffset = this.getPredictedBufferIndex(index, inRange, down);

        if (!inRange) {
            this.showLoadMask(true);
        }

        this.ds.suspendEvents();
        var sInfo  = this.ds.sortInfo;

        var params = {};
        if (this.ds.lastOptions) {
            Ext.apply(params, this.ds.lastOptions.params);
        }

        params.start = bufferOffset;
        params.limit = this.ds.bufferSize;

        if (sInfo) {
            params.dir  = sInfo.direction;
            params.sort = sInfo.field;
        }

        var opts = {
            forceRepaint     : forceRepaint,
            callback         : this.liveBufferUpdate,
            scope            : this,
            params           : params,
            // Zenoss change begins
            //suspendLoadEvent : true
            suspendLoadEvent : suspendLoadEvent
            // Zenoss change ends
        };

        this.fireEvent('beforebuffer', this, this.ds, index,
            Math.min(this.ds.totalLength, this.visibleRows-this.rowClipped),
            this.ds.totalLength, opts
        );

        this.ds.load(opts);
        this.ds.resumeEvents();
    },

    adjustBufferInset : function(){
        var liveScrollerDom = this.liveScroller.dom;
        var g = this.grid, ds = g.store;
        var c  = g.getGridEl();
        var elWidth = c.getSize().width;

        // hidden rows is the number of rows which cannot be
        // displayed and for which a scrollbar needs to be
        // rendered. This does also take clipped rows into account
        var hiddenRows;
        if (ds.totalLength == this.visibleRows-this.rowClipped) {
          hiddenRows = 0;
        } else {
          hiddenRows = Math.max(0, ds.totalLength-(this.visibleRows-this.rowClipped));
        }

        if (hiddenRows === 0) {
            this.scroller.setWidth(elWidth);
            liveScrollerDom.style.display = 'none';
            return;
        } else {
            this.scroller.setWidth(elWidth-(this.scrollOffset||0));
            liveScrollerDom.style.display = '';
        }

        var scrollbar = this.cm.getTotalWidth()+this.scrollOffset > elWidth;

        // adjust the height of the scrollbar
        var contHeight = liveScrollerDom.parentNode.offsetHeight - this.hdHeight;
        if ( ds.totalLength > 0 && scrollbar ) {
            contHeight -= this.horizontalScrollOffset;
        }

        liveScrollerDom.style.height = Math.max(contHeight, this.horizontalScrollOffset*2)+"px";

        if (this.rowHeight == -1) {
            return;
        }

        this.liveScrollerInset.style.height = (hiddenRows === 0 ? 0 : contHeight+(hiddenRows*this.rowHeight))+"px";
     }
});       
})(); // End local scope
