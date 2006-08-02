import pydot

class NetworkGraph(object):
    '''
    This class is a wrapper for pydot functionality. It provides a means of
    graphically representing nodes in a tree.
    '''
    def __init__(self, device=None, node=None, parentName=None):
        if device:
            raise NotImplemented
            self.node = None
        elif node:
            self.node = node
        self.parentName = parentName
        self.format = 'png'

    def simpleProcessNodes(self, node=None, parentName=None, doNets=False,
        doDevices=False):
        '''
        This method processes the child nodes of the passed node, and then its
        children. It returns a list of tuples where the tuples represent a
        simple parent-child relationship.
        '''
        if not node:
            node = self.node
        if not parentName:
            parentName = self.parentName
        edges = []
        if doNets and hasattr(node, 'nets'):
            edges.extend([ (parentName, x.ip) for x in node.nets if x.ip != 'default'])
        for childNode in node.children:
            childName = '%s' % (childNode.pj.hostname)
            if parentName:
                edges.append((parentName, childName))
            moreEdges = self.simpleProcessNodes(childNode, childName, doNets=doNets)
            edges.extend(moreEdges)
        return edges

    def complexProcessNodes(self):
        '''
        This method (will) processes nodes and builds the graphs node at a time
        with actual pydot objects (as opposed to building a graph from a list
        of edges). This allows for custom presentation changes based on node
        attributes.
        '''
        raise NotImplemented

    def setGraphFromEdges(self, edges, directed=True):
        graph = pydot.graph_from_edges(edges, directed=directed)
        graph.ranksep = '1.5'
        graph.format = self.format
        graph.bgcolor = '#EEEEEE'
        # the following don't seem to be working right now
        graph.fillcolor = '#5A6F8F'
        graph.fontcolor = '#FFFFFF'
        graph.fontsize = '10.0'
        graph.fontname = 'Helvetica'
        graph.style = 'filled'
        self.graph = graph

    def prepare(self, nodeProcessing='simple', edges=None):
        if nodeProcessing == 'simple':
            processNodes = self.simpleProcessNodes
            if not edges:
                edges = processNodes(doNets=self.withNetworks)
            self.setGraphFromEdges(edges)
        else:
            raise NotImplemented
            processNodes = self.complexProcessNodes
            

    def write(self, fdOrPath, format='png'):
        if hasattr(fdOrPath, 'write'):
            data = self.graph.create(format=format)
            fdOrPath.write(data)
        elif isinstance(fdOrPath, str):
            self.graph.write(fdOrPath)
        else:
            raise TypeError, "Unknown parameter for filename or file handle."

    def render(self, format='png', withNetworks=False):
        '''
        This will render an image format suitable for display in a browser.
        '''
        self.withNetworks = withNetworks
        self.prepare()
        return self.graph.create(format=format)

'''
scp /tmp/graph_from_edges_dot.svg oubiwann@192.168.1.115:

* Give a device name
* Find device and get node
* input node
* output to given file or stdout
* turn on/off networks
* turn on/off devices
* look at nets[0].pingjobs -- should be the list of things to ping on that
* network

processNode should allow one to indicate whether or not networks, devices,
etc., should be displayed
'''
