from zope.interface import Interface, Attribute


class ITreeNode(Interface):
    """
    Represents a single branch or leaf in a tree.
    """
    id = Attribute('The ID of the node, e.g. Processes/Apache/httpd')
    text = Attribute('The text label that represents the node')
    children = Attribute("The node's children")
    leaf = Attribute('Is this node a leaf (incapable of having children)')


class ITreeFacade(Interface):
    """
    Exposes methods for working with tree hierarchies.
    """
    def getTree(root):
        """
        Get the tree of instances.

        Returns the node identified by C{root}, which can be walked using the
        C{children} attribute.
        """
