function DirectedAcyclicGraph() {

    var layout_count = 0;
    var animate = true;

    /*
     * Main rendering function
     */
    function graph(selection) {
        selection.each(function(data) {
            // Select the g element that we draw to, or add it if it doesn't exist
            var svg = d3.select(this).selectAll("svg").data([data]);
            svg.enter().append("svg").append("g").attr("class", "graph").classed("animate", animate);

            // Size the chart
            svg.attr("width", width.call(this, data));
            svg.attr("height", height.call(this, data));

            // Get the edges and nodes from the data.  Can have user-defined accessors
            var edges = getedges.call(this, data);
            var nodes = getnodes.call(this, data);

            // Get the existing nodes and edges, and recalculate the node size
            var existing_edges = svg.select(".graph").selectAll(".edge").data(edges, edgeid);
            var existing_nodes = svg.select(".graph").selectAll(".node").data(nodes, nodeid);
            var clickable_edges = svg.select(".graph").selectAll(".largeEdge").data(edges, edgeid);

            // Capture the "preexisting" nodes before adding enter nodes to existing nodes
            existing_nodes.classed("pre-existing", true);
            existing_nodes.each(updatenode);

            var removed_edges = existing_edges.exit();
            var removed_nodes = existing_nodes.exit();
            var removed_large_edges = clickable_edges.exit();

            var new_edges = existing_edges.enter().insert("path", ":first-child").attr("class", "edge entering");
            var new_nodes = existing_nodes.enter().append("g").attr("class", "node entering");
            var new_large_edges = existing_edges.enter().insert("path", ":first-child").attr("class", "largeEdge entering");

            // Draw new nodes
            new_nodes.each(drawnode);
            existing_nodes.each(sizenode);
            if (animate) {
                removed_edges.classed("visible", false).transition().duration(500).remove();
            } else {
                removed_edges.classed("visible", false).remove();
                removed_large_edges.remove();
            }

            // Do the layout
            layout.call(svg.select(".graph").node(), nodes, edges);
            existing_nodes.classed("pre-existing", false);

            // Remove nodes after layout, allowing for access to post layout positions for other nodes
            removed_nodes.each(removenode);

            // Animate into new positions
            if (animate) {
                svg.select(".graph").selectAll(".edge.visible").transition().duration(800).attrTween("d", graph.edgeTween);//attr("d", graph.splineGenerator);
                existing_nodes.transition().duration(800).attr("transform", graph.nodeTranslate);
            } else {
                svg.select(".graph").selectAll(".edge.visible").attr("d", graph.splineGenerator);
                svg.select(".graph").selectAll(".largeEdge.visible").attr("d", graph.splineGenerator);
                existing_nodes.attr("transform", graph.nodeTranslate);
            }

            new_nodes.each(newnodetransition);
            new_edges.attr("d", graph.splineGenerator).classed("visible", true);
            new_large_edges.attr("d", graph.splineGenerator).classed("visible", true);

            existing_nodes.classed("visible", true);
            window.setTimeout(function() {
                new_edges.classed("entering", false);
                new_large_edges.classed("entering", false);
                new_nodes.classed("entering", false);
            }, 2000);
        });

    }


    /*
     * Settable variables and functions
     */
    var width = d3.functor("100%");
    var height = d3.functor("100%");
    var edgeid = function(d) { return d.source.id + d.target.id; }
    var nodeid = function(d) { return d.id; }
    var getnodes = function(d) { return d.getVisibleNodes(); }
    var getedges = function(d) { return d.getVisibleLinks(); }
    var d3interpolate = function(d) {
        return "basis";
    };
    var nodewidth = function(d) {
        return 60;
    }
    var nodeheight = function(d) {
        return 45;
    };
    var bbox = function(d) {
        return d3.select(this).select("rect").node().getBBox();
    }
    var drawnode = function(d) {
        // Attach box
        d3.select(this).append("rect").attr("rx", 4);

        // Attach node text
        d3.select(this).append("text").text(nodeid);

        var prior_pos = nodepos.call(this, d);
        if (prior_pos!=null) {
            d3.select(this).attr("transform", graph.nodeTranslate);
        }
    }
    var updatenode = function(d){
        drawnode(d);
    }

    var sizenode = function(d) {
        // Because of SVG weirdness, call sizenode as necessary to ensure a node's size is correct
        var node_bbox = {"height": nodeheight.call(this, d), "width": nodewidth.call(this, d)};
        var rect = d3.select(this).select('rect');
        var policyMarker = d3.select(this).select('.policy rect');
        var policyMarkerText = d3.select(this).select('.policy text');
        var collapseMarker = d3.select(this).select(".collapse");
        var text = d3.select(this).select(".nodeRep");
        var eventRainbowText = d3.select(this).select(".eventRainbow .eventRep");

        rect.attr("x", -node_bbox.width/2)
            .attr("y", -node_bbox.height/2)
            .attr("width", node_bbox.width)
            .attr("height", node_bbox.height);

        collapseMarker.attr("x1", -20).attr("y1", 45).attr("x2", 20).attr("y2", 45);

        if(!policyMarker.empty()){
            policyMarker.attr("x", -20).attr("y", node_bbox.height/2 - 5).attr("width", 40).attr("height", 10);
            policyMarkerText.attr("x", -policyMarkerText.node().getBBox().width/2).attr("y", node_bbox.height/2 + 3);
        }

        if(!eventRainbowText.empty()){
            eventRainbowText.attr("width", 35)
                .attr("height", node_bbox.height - 8)
                .attr("x", node_bbox.width/2)
                .attr("y", -node_bbox.height/2 + 7.5);

        }

        text.attr("x", -node_bbox.width/2).attr("y", -node_bbox.height/2);
        text.attr("width", node_bbox.width).attr("height", node_bbox.height);
    }
    var removenode = function(d) {
        if (animate) {
            d3.select(this).classed("visible", false).transition().duration(200).remove();
        } else {
            d3.select(this).classed("visible", false).remove();
        }
    }
    var newnodetransition = function(d) {
        d3.select(this).classed("visible", true).attr("transform", graph.nodeTranslate);
    }
    var customlayout = function(nodes_d, edges_d) {
        d3.select(this).selectAll(".edge").each(function(d) {
            var p = d.dagre.points;
            p.push(dagre.util.intersectRect(d.target.dagre, p.length > 0 ? p[p.length - 1] : d.source.dagre));
            p.splice(0, 0, dagre.util.intersectRect(d.source.dagre, p[0]));
            p.splice(1, 0, {x: p[0].x, y: p[0].y+15});
            p[0].y -= 0.5; p[p.length-1].y += 0.5;
        });
    };

    var layout = function(nodes_d, edges_d) {
        // Dagre requires the width, height, and bbox of each node to be attached to that node's data
        var start = new Date().getTime();
        d3.select(this).selectAll(".node").each(function(d) {
            d.bbox = bbox.call(this, d);
            d.width = d.bbox.width;
            d.height = d.bbox.height;
            d.dagre_prev = d.dagre_id==layout_count ? d.dagre : null;
            d.dagre_id = layout_count+1;
        });
        d3.select(this).selectAll(".edge").each(function(d) {
            d.dagre_prev = d.dagre_id==layout_count ? d.dagre : null;
            d.dagre_id = layout_count+1;
        });

        layout_count++;
        console.log("layout:bbox", (new Date().getTime() - start));

        // Call dagre layout.  Store layout data such that calls to x(), y() and points() will return them

        start = new Date().getTime();
        dagre.layout().nodeSep(15).edgeSep(30).rankSep(120).nodes(nodes_d).edges(edges_d).run();
        customlayout(nodes_d, edges_d);

        console.log("layout:dagre", (new Date().getTime() - start));

        // Also we want to make sure that the control points for all the edges overlap the nodes nicely


        // Try to put the graph as close to previous position as possible
        var count = 0, x = 0, y = 0;
        d3.select(this).selectAll(".node.pre-existing").each(function(d) {
            if (d.dagre_prev) {
                count++;
                x += (d.dagre_prev.x - d.dagre.x);
                y += (d.dagre_prev.y - d.dagre.y);
            }
        });
        if (count > 0) {
            x = x / count;
            y = y / count;
            d3.select(this).selectAll(".node").each(function(d) {
                d.dagre.x += x;
                d.dagre.y += y;
            })
            d3.select(this).selectAll(".edge").each(function(d) {
                d.dagre.points.forEach(function(p) {
                    p.x += x;
                    p.y += y;
                })
            })
        }
    }
    var nodepos = function(d) {
        // Returns the {x, y} location of a node after layout
        return d.dagre;
    }
    var edgepos = function(d) {
        // Returns a list of {x, y} control points of an edge after layout
        return d.dagre.points;
    }


    /*
     * A couple of private non-settable functions
     */
    graph.splineGenerator = function(d) {
        return d3.svg.line().x(function(d) { return d.x })
                            .y(function(d) { return d.y})
                            .interpolate(d3interpolate.call(this, d))(edgepos.call(this, d));
    }

    graph.edgeTween = function(d) {
        var src = d.dagre_prev ? d.dagre_prev.points : d.dagre.points;
        var dst = d.dagre.points;
        var points = d3.range(Math.max(src.length, dst.length)).map(function(i){
            var p0 = src[Math.min(src.length-1, i)];
            var p1 = dst[Math.min(dst.length-1, i)];
            return d3.interpolate([p0.x, p0.y], [p1.x, p1.y]);
        });
        var line = d3.svg.line().interpolate(d3interpolate.call(this));
        return function(t) {
            return line(points.map(function(p) { return p(t); }));
        };
    }

    graph.nodeTranslate = function(d) {
        var pos = nodepos.call(this, d);
        return "translate(" + pos.x + "," + pos.y + ")";
    }

    function random(min, max) {
        return function() { return min + (Math.random() * (max-min)); }
    }


    /*
     * Getters and setters for settable variables and function
     */
    graph.width = function(_) { if (!arguments.length) return width; width = d3.functor(_); return graph; }
    graph.height = function(_) { if (!arguments.length) return height; height = d3.functor(_); return graph; }
    graph.edgeid = function(_) { if (!arguments.length) return edgeid; edgeid = _; return graph; }
    graph.nodeid = function(_) { if (!arguments.length) return nodeid; nodeid = _; return graph; }
    graph.nodename = function(_) { if (!arguments.length) return nodename; nodename = _; return graph; }
    graph.nodes = function(_) { if (!arguments.length) return getnodes; getnodes = d3.functor(_); return graph; }
    graph.edges = function(_) { if (!arguments.length) return getedges; getedges = d3.functor(_); return graph; }
    graph.bbox = function(_) { if (!arguments.length) return bbox; bbox = d3.functor(_); return graph; }
    graph.nodeTemplate = function(_) { if (!arguments.length) return nodeTemplate; nodeTemplate = _; return graph; }
    graph.drawnode = function(_) { if (!arguments.length) return drawnode; drawnode = _; return graph; }
    graph.updatenode = function(_) { if (!arguments.length) return updatenode; updatenode = _; return graph; }
    graph.removenode = function(_) { if (!arguments.length) return removenode; removenode = _; return graph; }
    graph.newnodetransition = function(_) { if (!arguments.length) return newnodetransition; newnodetransition = _; return graph; }
    graph.layout = function(_) { if (!arguments.length) return layout; layout = _; return graph; }
    graph.nodepos = function(_) { if (!arguments.length) return nodepos; nodepos = _; return graph; }
    graph.edgepos = function(_) { if (!arguments.length) return edgepos; edgepos = _; return graph; }
    graph.animate = function(_) { if (!arguments.length) return animate; animate = _; return graph; }
    graph.getedges = function(_) { if (!arguments.length) return getedges; getedges = _; return graph;}
    graph.d3interpolation = function(_) { if (!arguments.length) return d3interpolate; d3interpolate = _; return graph;}
    graph.nodewidth = function(_) { if (!arguments.length) return nodewidth; nodewidth = _; return graph;}
    graph.nodeheight = function(_) { if (!arguments.length) return nodeheight; nodeheight = _; return graph;}
    graph.customlayout = function(_) { if (!arguments.length) return customlayout; customlayout = _; return graph;}

    return graph;
}