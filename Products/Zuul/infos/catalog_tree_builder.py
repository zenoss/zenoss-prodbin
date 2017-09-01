##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
from collections import defaultdict

from Products.AdvancedQuery import And, Eq, MatchGlob
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.Zuul.catalog.model_catalog import OBJECT_UID_FIELD as UID

log = logging.getLogger("catalog_tree_builder")


class ModelCatalogTreeNode(object):
    def __init__(self, path):
        self.path = path
        self.id = path.split("/")[-1]
        self.child_trees = {}
        self.partial_leaf_count = 0   # count not including children
        self.total_leaf_count = 0     # count including children


class ModelCatalogTreeBuilder(object):
    """
    Builds a Navigation Tree using Model Catalog 
    """
    def __init__(self, root, node_type, leaf_type, facet_field=None, unique_leaves=True):
        """
        @param root:            root node of the tree
        @param node_type:       value of the object_implements field to query the catalog for nodes
                                    Ex: "Products.ZenModel.DeviceOrganizer.DeviceOrganizer"
        @param leaf_type:       value of the object_implements field to query the catalog for leaves
                                    Ex: "Products.ZenModel.Device.Device"
        @param facet_field:     field to retrieve leaf count using facets
        @param unique_leaves:   indicates if a leave can belong to more than one node or not. It conditions
                                how the total leaf count is calculated
        """
        self.root = root               # root object for which we are building the tree
        self.brains = {}               # obj_uid : obj brain
        self.trees = {}                # obj_uid : ModelCatalogTreeNode
        self.root_tree = None
        self.root_path = "/".join(self.root.getPrimaryPath())
        self.model_catalog = IModelCatalogTool(self.root.dmd)
        self.node_objectImplements = node_type
        self.leaf_objectImplements = leaf_type
        self.facet_field = facet_field
        self.unique_leaves = unique_leaves
        # Build the cache
        self.build_tree()

    def _query_catalog(self, objectImplements, filter_permissions=True, limit=None, fields=None, facet_field=None):
        requested_fields = set([ UID, "name", "id", "uuid" ])
        params = {}
        params["types"] = objectImplements
        params["paths"] = self.root_path
        if fields:
            if isinstance(fields, basestring):
                fields = [fields]
            requested_fields |= set(fields)
        params["fields"] = list(requested_fields)
        params["filterPermissions"] = filter_permissions
        if limit:
            params["limit"] = limit
        if facet_field:
            params["facets_for_field"] = facet_field
        return self.model_catalog.search(**params)

    def build_tree(self):
        """
        Builds the tree for a given root node and its subtrees
        """
        # Load the nodes
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

        # Two ways of calculating the total leaf count depending on if leaves are unique in the tree or not:
        #    - Adding the partial counts starting from the bottom of the tree and going up
        #    - If leaves can be under more than one node, to calculate the total we need to
        #      get all the leaves and manually count them so they are no accounted more than once
        if self.unique_leaves:
            self._load_leaf_counts_using_facets()
        else:
            self._load_not_unique_leaf_counts()

    def _load_leaf_counts_using_facets(self):
        # facets values are returned in lower case
        path_translator = {}
        for tree_path in self.trees.iterkeys():
            lower_case_path = tree_path.lower()
            path_translator[lower_case_path] = tree_path

        # query to retrieve the counts using facets
        search_results = self._query_catalog(self.leaf_objectImplements, limit=0, facet_field=self.facet_field)

        # load the partial child counts using facets
        if search_results.facets and search_results.facets.get(self.facet_field):
            facets = search_results.facets[self.facet_field]
            for lower_case_path, count in facets.iteritems():
                real_path = path_translator.get(lower_case_path)
                if real_path:
                    self.trees[real_path].partial_leaf_count = count
            # Calculate the total leaf count adding up the partial counts
            nodes_uids = self.trees.keys()
            nodes_uids.sort(reverse=True, key=lambda x: len(x))
            for node_uid in nodes_uids:
                current_tree = self.trees[node_uid]
                leaf_count = 0
                for child_tree in current_tree.child_trees.itervalues():
                    leaf_count += child_tree.total_leaf_count
                current_tree.total_leaf_count = current_tree.partial_leaf_count + leaf_count

    def _get_child_trees(self, node_uid):
        """
        Given a node's uid, it returns the uids of all the nodes
        under it including itself
        """
        child_trees = set()
        to_process = { self.trees[node_uid] }
        while to_process:
            current_tree = to_process.pop()
            child_trees.add(current_tree.path)
            for child_tree in current_tree.child_trees.itervalues():
                to_process.add(child_tree)
        return child_trees

    def _load_not_unique_leaf_counts(self):
        leaves_per_node = defaultdict(set)
        # load all leaves for the tree and it subtrees
        search_results = self._query_catalog(self.leaf_objectImplements, fields="deviceOrganizers")
        for child_brain in search_results.results:
            nodes = set()
            # get the organizers this leaf belongs to
            for node_uid in child_brain.deviceOrganizers:
                if node_uid.startswith(self.root_path):
                    nodes.add(node_uid)
            # add the leaf uid to the organizers it belongs to
            for node_uid in nodes:
                if node_uid in self.trees:
                    leaves_per_node[node_uid].add(child_brain.uid)

        # Get the total count by counting the number of unique leaves under each node
        nodes_uids = self.trees.keys()
        nodes_uids.sort(reverse=True, key=lambda x: len(x))
        for node_uid in nodes_uids:
            current_tree = self.trees[node_uid]
            leaves_under_current_tree = set()
            subtrees = self._get_child_trees(node_uid)
            for subtree_uid in subtrees:
                leaves_under_current_tree |= leaves_per_node[subtree_uid]
            current_tree.total_leaf_count = len(leaves_under_current_tree)

    def get_children(self, node_path):
        tree = self.trees[node_path]
        subtrees = tree.child_trees.values()
        subtrees.sort( key=lambda x: x.id )
        brains = [ self.brains[subtree.path] for subtree in subtrees if self.brains.get(subtree.path)]
        return brains

    def get_leaf_count(self, node_path):
        count = 0
        node_tree = self.trees.get(node_path)
        if node_tree:
            count = node_tree.total_leaf_count
        return count