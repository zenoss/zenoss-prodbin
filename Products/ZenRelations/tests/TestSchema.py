#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

from ZenRelations.RelationshipManager import RelationshipManager

# Test schema classes see schema.data for relationships
class Device(RelationshipManager):pass
class Server(Device):pass
class IpInterface(RelationshipManager):pass
class Group(RelationshipManager):pass
class Location(RelationshipManager):pass
class Admin(RelationshipManager):pass
