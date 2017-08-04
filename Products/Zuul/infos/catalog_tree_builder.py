##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from Products.AdvancedQuery import And, Eq, MatchGlob
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.Zuul.catalog.model_catalog import OBJECT_UID_FIELD as UID

# TODO: Get the Networks tree to use this.

class ModelCatalogTreeNode(object):
    def __init__(self, path):
        self.path = path
        self.id = path.split("/")[-1]
        self.child_trees = {}
        self.partial_leave_count = 0   # count not including children
        self.total_leave_count = 0     # count including children


class ModelCatalogTreeBuilder(object):
    """
    Builds a Navigation Tree using Model Catalog 
    """
    def __init__(self, root, node_type, leave_type):
        """
        @param root:        root node of the tree
        @param node_type:   value of the object_implements field to query the catalog for nodes
                                Ex: "Products.ZenModel.DeviceOrganizer.DeviceOrganizer"
        @param leave_type:  value of the object_implements field to query the catalog for leaves
                                Ex: "Products.ZenModel.Device.Device"
        """
        self.root = root               # root object for which we are building the tree
        self.brains = {}               # obj_uid : obj brain
        self.trees = {}                # obj_uid : ModelCatalogTreeNode
        self.root_tree = None
        self.root_path = "/".join(self.root.getPrimaryPath())
        self.model_catalog = IModelCatalogTool(self.root.dmd)
        self.node_objectImplements = node_type
        self.leave_objectImplements = leave_type
        # Build the cache
        self.build_tree()
        self.load_leave_counts()

    def _query_catalog(self, objectImplements, filter_permissions=True):
        type_query = Eq("objectImplements", objectImplements)
        path_query = MatchGlob("path", "{}*".format(self.root_path))
        fields = [ UID, "name", "id", "uuid" ]
        return self.model_catalog.search(query=And(type_query, path_query), fields=fields, filterPermissions=filter_permissions)

    def build_tree(self):
        """
        Builds the tree for a given root node and its subtrees
        """
        search_results = self._query_catalog(self.node_objectImplements, filter_permissions=False)
        nodes = set()
        for brain in search_results.results:
            self.brains[brain.uid] = brain
            nodes.add(brain.uid)

        self.root_tree = ModelCatalogTreeNode(self.root_path)
        self.trees[self.root_path] = self.root_tree

        for path in nodes:
            if not path.startswith(self.root_path) or \
               path == self.root_path:
                continue
            current_path = self.root_path
            current_tree = self.root_tree

            # get subtrees
            # Example:
            #    root:       /zport/dmd/Devices
            #    path:       /zport/dmd/Devices/Server/Linux
            #    subtrees:   Server
            #                Server/Linux
            #
            subtrees = path.replace(self.root_path, "").strip("/").split("/")

            for subtree in subtrees:
                if not subtree:
                    continue
                current_path = "{}/{}".format(current_path, subtree)
                if subtree not in current_tree.child_trees:
                    new_tree = ModelCatalogTreeNode(current_path)
                    current_tree.child_trees[subtree] = new_tree
                    self.trees[current_path] = new_tree
                current_tree = current_tree.child_trees[subtree]

    def load_leave_counts(self):
        # TODO Investigate if this would be faster using solr facets
        # load all leaves for the tree and it subtrees
        search_results = self._query_catalog(self.leave_objectImplements)
        for child_brain in search_results.results:
            # Get the parent node path
            parent_path = "/".join(child_brain.uid.split("/")[:-2])
            if parent_path in self.trees:
                self.trees[parent_path].partial_leave_count += 1

        # Now get the total child count per node from the bottom up
        nodes_uids = self.trees.keys()
        nodes_uids.sort(reverse=True, key=lambda x: len(x))
        for node_uid in nodes_uids:
            current_tree = self.trees[node_uid]
            leave_count = 0
            for child_tree in current_tree.child_trees.itervalues():
                leave_count += child_tree.total_leave_count
            current_tree.total_leave_count = current_tree.partial_leave_count + leave_count

    def _tree_to_str(self, current_tree=None, level=1):
        lines = []
        if current_tree is None:
            current_tree = self.root_tree
        lines.append("{}{} ({})".format('  '*level, current_tree.id.ljust(15), current_tree.total_leave_count))
        for child_tree in current_tree.child_trees.itervalues():
            self._print_tree(child_tree, level+1)
        return "\n".join(lines)

    def get_children(self, node_path):
        tree = self.trees[node_path]
        subtrees = tree.child_trees.values()
        subtrees.sort( key=lambda x: x.id )
        brains = [ self.brains[subtree.path] for subtree in subtrees if self.brains.get(subtree.path)]
        return brains

    def get_leave_count(self, node_path):
        count = 0
        node_tree = self.trees.get(node_path)
        if node_tree:
            count = node_tree.total_leave_count
        return count