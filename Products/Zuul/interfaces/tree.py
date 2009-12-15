from zope.interface import Interface, Attribute

from Products.Zuul.interfaces import IMarshallable


class ITreeNode(IMarshallable):
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

class ITreeWalker(Interface):
    """
    Adapts a member of the ZenRelations hierarchy. Provides uniform
    API for requesting contained children.
    """
    def rawChildren(self):
        """
        Returns representations of children that are able to get the 
        represented object when asked (brains, or BrainWhilePossibles, or
        the object itself). 

        This method is meant to be called by other TreeWalkers or by 
        subclasses, so that filtering and sorting can be done later.
        """
    def children(self):
        """
        Returns consumable children, i.e. the actual children themselves.

        This method is meant to be called directly. It is the entry point for
        non-walkers.
        """
        
class IEntityManager(Interface):
    """
    Adapts an organizer. Provides a way to query for lazy batches of children by 
    type and sort the results.
    """
    def children(self):
        """
        Get some children
        """