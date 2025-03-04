SOLR_HOST="solr"

# Increase Java Heap as needed to support your indexing / query needs
SOLR_HEAP="1500m"

# Sets the network interface the Solr binds to. To prevent administrators from
# accidentally exposing Solr more widely than intended, this defaults to 127.0.0.1.
# Administrators should think carefully about their deployment environment and
# set this value as narrowly as required before going to production. In
# environments where security is not a concern, 0.0.0.0 can be used to allow
# Solr to accept connections on all network interfaces.
#SOLR_JETTY_HOST="127.0.0.1"
#SOLR_JETTY_HOST="0.0.0.0"

# Runs solr in java security manager sandbox. This can protect against some attacks.
# Runtime properties are passed to the security policy file (server/etc/security.policy)
# You can also tweak via standard JDK files such as ~/.java.policy, see https://s.apache.org/java8policy
# This is experimental! It may not work at all with Hadoop/HDFS features.
#SOLR_SECURITY_MANAGER_ENABLED=true
SOLR_SECURITY_MANAGER_ENABLED=false

# SOLR_OPTS="-Dsolr.http1=true -Dsolr.jetty.host=0.0.0.0"
SOLR_OPTS="-Dsolr.http1=true"
