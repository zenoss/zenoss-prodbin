(function(){ // Local scope
Ext.override(Ext.ux.grid.livegrid.GridView, {
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
