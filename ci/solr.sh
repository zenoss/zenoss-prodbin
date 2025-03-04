#!/usr/bin/env bash
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# CONTROLLING STARTUP:
#
# Use solr -help to see available command-line options. In addition
# to passing command-line options, this script looks for an include
# file named solr.in.sh to set environment variables. Specifically,
# the following locations are searched in this order:
#
# <script location>/.
# $HOME/.solr.in.sh
# /usr/share/solr
# /usr/local/share/solr
# /etc/default
# /var/solr
# /opt/solr
#
# Another option is to specify the full path to the include file in the
# environment. For example:
#
#   $ SOLR_INCLUDE=/path/to/solr.in.sh solr start
#
# Note: This is particularly handy for running multiple instances on a
# single installation, or for quick tests.
#
# Finally, developers and enthusiasts who frequently run from an SVN
# checkout, and do not want to locally modify bin/solr.in.sh, can put
# a customized include file at ~/.solr.in.sh.
#
# If you would rather configure startup entirely from the environment, you
# can disable the include by exporting an empty SOLR_INCLUDE, or by
# ensuring that no include files exist in the aforementioned search list.

SOLR_SCRIPT="$0"
verbose=false
THIS_OS=$(uname -s)

# What version of Java is required to run this version of Solr.
JAVA_VER_REQ=11

stop_all=false

# for now, we don't support running this script from cygwin due to problems
# like not having lsof, ps auxww, curl, and awkward directory handling
if [ "${THIS_OS:0:6}" == "CYGWIN" ]; then
  echo -e "This script does not support cygwin due to severe limitations and lack of adherence\nto BASH standards, such as lack of lsof, curl, and ps options.\n\nPlease use the native solr.cmd script on Windows!"
  exit 1
fi
# Alpine Linux BusyBox comes with a stripped down ps, make sure we have a fully featured one
# shellcheck disable=SC2046
if [ $$ -ne $(ps -o pid='' -p $$ || echo 0) ] ; then
  echo -e "This script relies on a version of ps that supports the -p flag.\n\nPlease install a POSIX compliant version and try again."
  exit 1
fi

# This helps with debugging when running bats tests but not the whole script is compliant yet
# set -u
# set -o pipefail

# Resolve symlinks to this script
while [ -h "$SOLR_SCRIPT" ] ; do
  ls=$(ls -ld "$SOLR_SCRIPT")
  # Drop everything prior to ->
  link=$(expr "$ls" : '.*-> \(.*\)$')
  if expr "$link" : '/.*' > /dev/null; then
    SOLR_SCRIPT="$link"
  else
    SOLR_SCRIPT=$(dirname "$SOLR_SCRIPT")/"$link"
  fi
done

CDPATH=''  # Prevent "file or directory not found" for 'cdpath' users
SOLR_TIP=$(dirname "$SOLR_SCRIPT")/..
# shellcheck disable=SC2164
SOLR_TIP_SYM=$(cd "$SOLR_TIP"; pwd -L)
# shellcheck disable=SC2164
SOLR_TIP=$(cd "$SOLR_TIP"; pwd -P)
DEFAULT_SERVER_DIR="$SOLR_TIP/server"

# If an include wasn't specified in the environment, then search for one...
if [[ -z "${SOLR_INCLUDE:-}" ]]; then
  # Locations (in order) to use when searching for an include file.
  for include in "$(dirname "$0")/solr.in.sh" \
               "$HOME/.solr.in.sh" \
               /usr/share/solr/solr.in.sh \
               /usr/local/share/solr/solr.in.sh \
               /etc/default/solr.in.sh \
               /var/solr/solr.in.sh \
               /opt/solr/solr.in.sh; do
    if [ -r "$include" ]; then
        SOLR_INCLUDE="$include"
        . "$include"
        break
    fi
  done
elif [ -r "$SOLR_INCLUDE" ]; then
  . "$SOLR_INCLUDE"
fi

# Export variables we want to make visible to Solr sub-process
for var in $(compgen -v); do
  if [[ "$var" =~ ^(SOLR_.*|DEFAULT_CONFDIR|ZK_.*|GCS_BUCKET|GCS_.*|S3_.*|OTEL_.*|AWS_.*)$ ]]; then
    export "${var?}"
  fi
done

# if pid dir is unset, default to $solr_tip/bin
: "${SOLR_PID_DIR:=$SOLR_TIP/bin}"

if [ -n "${SOLR_JAVA_HOME:-}" ]; then
  JAVA="$SOLR_JAVA_HOME/bin/java"
  JSTACK="$SOLR_JAVA_HOME/bin/jstack"
elif [ -n "${JAVA_HOME:-}" ]; then
  for java in "$JAVA_HOME"/bin/amd64 "$JAVA_HOME"/bin; do
    if [ -x "$java/java" ]; then
      JAVA="$java/java"
      if [ -x "$java/jstack" ]; then
        JSTACK="$java/jstack"
      elif [ -x "$(command -v jattach)" ]; then
        JATTACH="$(command -v jattach)"
      else
        echo >&2 "neither jattach nor jstack in $JAVA_HOME could be found, so no thread dumps are possible. Continuing."
      fi
      break
    fi
  done
  if [ -z "$JAVA" ]; then
    echo >&2 "The currently defined JAVA_HOME ($JAVA_HOME) refers"
    echo >&2 "to a location where Java could not be found.  Aborting."
    echo >&2 "Either fix the JAVA_HOME variable or remove it from the"
    echo >&2 "environment so that the system PATH will be searched."
    exit 1
  fi
else
  JAVA=java
  JSTACK=jstack
fi

: "${SOLR_STOP_WAIT:=180}"
: "${SOLR_START_WAIT:=$SOLR_STOP_WAIT}" # defaulting to $SOLR_STOP_WAIT for backwards compatibility reasons

# Store whether a solr port was explicitly provided, for the "solr stop" command.
PROVIDED_SOLR_PORT="${SOLR_PORT:-}"
: "${SOLR_PORT:=8983}"
export SOLR_PORT

# test that Java exists, is executable and correct version
JAVA_VER=$("$JAVA" -version 2>&1)
# shellcheck disable=SC2181
if [[ $? -ne 0 ]] ; then
  echo >&2 "Java not found, or an error was encountered when running java."
  echo >&2 "A working Java $JAVA_VER_REQ JRE is required to run Solr!"
  echo >&2 "Please install latest version of Java $JAVA_VER_REQ or set JAVA_HOME properly."
  echo >&2 "Command that we tried: '${JAVA} -version', with response:"
  echo >&2 "${JAVA_VER}"
  echo >&2
  echo >&2 "Debug information:"
  echo >&2 "JAVA_HOME: ${JAVA_HOME:-N/A}"
  echo >&2 "Active Path:"
  echo >&2 "${PATH}"
  exit 1
else
  JAVA_VER_NUM=$(echo "$JAVA_VER" | grep -v '_OPTIONS' | head -1 | awk -F '"' '/version/ {print $2}' | sed -e's/^1\.//' | sed -e's/[._-].*$//')
  if [[ "$JAVA_VER_NUM" -lt "$JAVA_VER_REQ" ]] ; then
    echo >&2 "Your current version of Java is too old to run this version of Solr."
    echo >&2 "We found major version $JAVA_VER_NUM, using command '${JAVA} -version', with response:"
    echo >&2 "${JAVA_VER}"
    echo >&2
    echo >&2 "Please install latest version of Java $JAVA_VER_REQ or set JAVA_HOME properly."
    echo >&2
    echo >&2 "Debug information:"
    echo >&2 "JAVA_HOME: ${JAVA_HOME:-N/A}"
    echo >&2 "Active Path:"
    echo >&2 "${PATH}"
    exit 1
  fi
  JAVA_VENDOR="Oracle"
   # OpenJ9 was previously known as IBM J9, this will match both
  if [ "$(echo "$JAVA_VER" | grep -i -E "OpenJ9|IBM J9")" != "" ]; then
      JAVA_VENDOR="OpenJ9"
  fi
fi


# Select HTTP OR HTTPS related configurations
SOLR_URL_SCHEME=http
SOLR_JETTY_CONFIG=()
SOLR_SSL_OPTS=""

if [ -n "${SOLR_HADOOP_CREDENTIAL_PROVIDER_PATH:-}" ]; then
  SOLR_SSL_OPTS+=" -Dhadoop.security.credential.provider.path=$SOLR_HADOOP_CREDENTIAL_PROVIDER_PATH"
fi

if [ -z "${SOLR_SSL_ENABLED:-}" ]; then
  if [ -n "${SOLR_SSL_KEY_STORE:-}" ]; then
    SOLR_SSL_ENABLED="true" # implicitly from earlier behaviour
  else
    SOLR_SSL_ENABLED="false"
  fi
fi
if [ "$SOLR_SSL_ENABLED" == "true" ]; then
  SOLR_JETTY_CONFIG+=("--module=https" "--lib=$DEFAULT_SERVER_DIR/solr-webapp/webapp/WEB-INF/lib/*")
  if [ "${SOLR_SSL_RELOAD_ENABLED:-true}" == "true" ]; then
    SOLR_JETTY_CONFIG+=("--module=ssl-reload")
    SOLR_SSL_OPTS+=" -Dsolr.keyStoreReload.enabled=true"
  fi
  SOLR_URL_SCHEME=https
  if [ -n "$SOLR_SSL_KEY_STORE" ]; then
    SOLR_SSL_OPTS+=" -Dsolr.jetty.keystore=$SOLR_SSL_KEY_STORE"
    if [ "${SOLR_SSL_RELOAD_ENABLED:-true}" == "true" ] && [ "${SOLR_SECURITY_MANAGER_ENABLED:-true}" == "true"  ]; then
      # In this case we need to allow reads from the parent directory of the keystore
      SOLR_SSL_OPTS+=" -Dsolr.jetty.keystoreParentPath=$SOLR_SSL_KEY_STORE/.."
    fi
  fi
  if [ -n "$SOLR_SSL_KEY_STORE_PASSWORD" ]; then
    export SOLR_SSL_KEY_STORE_PASSWORD=$SOLR_SSL_KEY_STORE_PASSWORD
  fi
  if [ -n "$SOLR_SSL_KEY_STORE_TYPE" ]; then
    SOLR_SSL_OPTS+=" -Dsolr.jetty.keystore.type=$SOLR_SSL_KEY_STORE_TYPE"
  fi

  if [ -n "$SOLR_SSL_TRUST_STORE" ]; then
    SOLR_SSL_OPTS+=" -Dsolr.jetty.truststore=$SOLR_SSL_TRUST_STORE"
  fi
  if [ -n "$SOLR_SSL_TRUST_STORE_PASSWORD" ]; then
    export SOLR_SSL_TRUST_STORE_PASSWORD=$SOLR_SSL_TRUST_STORE_PASSWORD
  fi
  if [ -n "$SOLR_SSL_TRUST_STORE_TYPE" ]; then
    SOLR_SSL_OPTS+=" -Dsolr.jetty.truststore.type=$SOLR_SSL_TRUST_STORE_TYPE"
  fi

  if [ "${SOLR_SSL_CLIENT_HOSTNAME_VERIFICATION:true}" == "true" ] ; then
    SOLR_SSL_OPTS+=" -Dsolr.jetty.ssl.verifyClientHostName=HTTPS"
  fi

  if [ -n "$SOLR_SSL_NEED_CLIENT_AUTH" ]; then
    SOLR_SSL_OPTS+=" -Dsolr.jetty.ssl.needClientAuth=$SOLR_SSL_NEED_CLIENT_AUTH"
  fi
  if [ -n "$SOLR_SSL_WANT_CLIENT_AUTH" ]; then
    SOLR_SSL_OPTS+=" -Dsolr.jetty.ssl.wantClientAuth=$SOLR_SSL_WANT_CLIENT_AUTH"
  fi

  if [ -n "$SOLR_SSL_CLIENT_KEY_STORE" ]; then
    SOLR_SSL_OPTS+=" -Djavax.net.ssl.keyStore=$SOLR_SSL_CLIENT_KEY_STORE"

    if [ -n "$SOLR_SSL_CLIENT_KEY_STORE_PASSWORD" ]; then
      export SOLR_SSL_CLIENT_KEY_STORE_PASSWORD=$SOLR_SSL_CLIENT_KEY_STORE_PASSWORD
    fi
    if [ -n "$SOLR_SSL_CLIENT_KEY_STORE_TYPE" ]; then
      SOLR_SSL_OPTS+=" -Djavax.net.ssl.keyStoreType=$SOLR_SSL_CLIENT_KEY_STORE_TYPE"
    fi
    if [ "${SOLR_SSL_RELOAD_ENABLED:-true}" == "true" ] && [ "${SOLR_SECURITY_MANAGER_ENABLED:-true}" == "true"  ]; then
      # In this case we need to allow reads from the parent directory of the keystore
      SOLR_SSL_OPTS+=" -Djavax.net.ssl.keyStoreParentPath=$SOLR_SSL_CLIENT_KEY_STORE/.."
    fi
  else
    if [ -n "$SOLR_SSL_KEY_STORE" ]; then
      SOLR_SSL_OPTS+=" -Djavax.net.ssl.keyStore=$SOLR_SSL_KEY_STORE"
    fi
    if [ -n "$SOLR_SSL_KEY_STORE_TYPE" ]; then
      SOLR_SSL_OPTS+=" -Djavax.net.ssl.keyStoreType=$SOLR_SSL_KEY_STORE_TYPE"
    fi
  fi

  if [ -n "$SOLR_SSL_CHECK_PEER_NAME" ]; then
    SOLR_SSL_OPTS+=" -Dsolr.ssl.checkPeerName=$SOLR_SSL_CHECK_PEER_NAME -Dsolr.jetty.ssl.sniHostCheck=$SOLR_SSL_CHECK_PEER_NAME"
  fi

  if [ -n "$SOLR_SSL_CLIENT_TRUST_STORE" ]; then
    SOLR_SSL_OPTS+=" -Djavax.net.ssl.trustStore=$SOLR_SSL_CLIENT_TRUST_STORE"

    if [ -n "$SOLR_SSL_CLIENT_TRUST_STORE_PASSWORD" ]; then
      export SOLR_SSL_CLIENT_TRUST_STORE_PASSWORD=$SOLR_SSL_CLIENT_TRUST_STORE_PASSWORD
    fi
    if [ -n "$SOLR_SSL_CLIENT_TRUST_STORE_TYPE" ]; then
      SOLR_SSL_OPTS+=" -Djavax.net.ssl.trustStoreType=$SOLR_SSL_CLIENT_TRUST_STORE_TYPE"
    fi
  else
    if [ -n "$SOLR_SSL_TRUST_STORE" ]; then
      SOLR_SSL_OPTS+=" -Djavax.net.ssl.trustStore=$SOLR_SSL_TRUST_STORE"
    fi

    if [ -n "$SOLR_SSL_TRUST_STORE_TYPE" ]; then
      SOLR_SSL_OPTS+=" -Djavax.net.ssl.trustStoreType=$SOLR_SSL_TRUST_STORE_TYPE"
    fi
  fi
else
  SOLR_JETTY_CONFIG+=("--module=http")
fi
export SOLR_URL_SCHEME

# Requestlog options
if [ "${SOLR_REQUESTLOG_ENABLED:-true}" == "true" ]; then
  SOLR_JETTY_CONFIG+=("--module=requestlog")
fi

# Jetty gzip module enabled by default
if [ "${SOLR_GZIP_ENABLED:-true}" == "true" ]; then
  SOLR_JETTY_CONFIG+=("--module=gzip")
fi

# Authentication options
if [ -z "${SOLR_AUTH_TYPE:-}" ] && [ -n "${SOLR_AUTHENTICATION_OPTS:-}" ]; then
  echo "WARNING: SOLR_AUTHENTICATION_OPTS environment variable configured without associated SOLR_AUTH_TYPE variable"
  echo "         Please configure SOLR_AUTH_TYPE environment variable with the authentication type to be used."
  echo "         Currently supported authentication types are [kerberos, basic]"
fi

if [ -n "${SOLR_AUTH_TYPE:-}" ] && [ -n "${SOLR_AUTHENTICATION_CLIENT_BUILDER:-}" ]; then
  echo "WARNING: SOLR_AUTHENTICATION_CLIENT_BUILDER and SOLR_AUTH_TYPE environment variables are configured together."
  echo "         Use SOLR_AUTH_TYPE environment variable to configure authentication type to be used. "
  echo "         Currently supported authentication types are [kerberos, basic]"
  echo "         The value of SOLR_AUTHENTICATION_CLIENT_BUILDER environment variable will be ignored"
fi

if [ -n "${SOLR_AUTH_TYPE:-}" ]; then
  case "$(echo "$SOLR_AUTH_TYPE" | awk '{print tolower($0)}')" in
    basic)
      SOLR_AUTHENTICATION_CLIENT_BUILDER="org.apache.solr.client.solrj.impl.PreemptiveBasicAuthClientBuilderFactory"
      ;;
    kerberos)
      SOLR_AUTHENTICATION_CLIENT_BUILDER="org.apache.solr.client.solrj.impl.Krb5HttpClientBuilder"
      ;;
    *)
      echo "ERROR: Value specified for SOLR_AUTH_TYPE environment variable is invalid."
      exit 1
   esac
fi

if [ -n "${SOLR_AUTHENTICATION_CLIENT_CONFIGURER:-}" ]; then
  echo "WARNING: Found unsupported configuration variable SOLR_AUTHENTICATION_CLIENT_CONFIGURER"
  echo "         Please start using SOLR_AUTH_TYPE instead"
fi
if [ -n "${SOLR_AUTHENTICATION_CLIENT_BUILDER:-}" ]; then
  AUTHC_CLIENT_BUILDER_ARG="-Dsolr.httpclient.builder.factory=$SOLR_AUTHENTICATION_CLIENT_BUILDER"
  AUTHC_OPTS="${AUTHC_CLIENT_BUILDER_ARG:-}"
fi
# This looks strange, but it is to avoid extra spaces when we have only one of the values set
AUTHC_OPTS="${AUTHC_OPTS:-}${SOLR_AUTHENTICATION_OPTS:+ $SOLR_AUTHENTICATION_OPTS}"

# Set the SOLR_TOOL_HOST variable for use when connecting to a running Solr instance
SOLR_TOOL_HOST="${SOLR_HOST:-localhost}"
export SOLR_TOOL_HOST

function print_usage() {
  CMD="${1:-}"
  ERROR_MSG="${2:-}"

  if [ -n "${ERROR_MSG:-}" ]; then
    echo -e "\nERROR: $ERROR_MSG\n"
  fi

  if [ -z "${CMD:-}" ]; then
    echo ""
    echo "Usage: solr COMMAND OPTIONS"
    echo "       where COMMAND is one of: start, stop, restart, status, healthcheck, create, create_core, create_collection, delete, version, zk, auth, assert, config, export, api, package, post, postlogs"
    echo ""
    echo "  Standalone server example (start Solr running in the background on port 8984):"
    echo ""
    echo "    ./solr start -p 8984"
    echo ""
    echo "  SolrCloud example (start Solr running in SolrCloud mode using localhost:2181 to connect to Zookeeper, with 1g max heap size and remote Java debug options enabled):"
    echo ""
    echo "    ./solr start -c -m 1g -z localhost:2181 -a \"-Xdebug -Xrunjdwp:transport=dt_socket,server=y,suspend=n,address=1044\""
    echo ""
    echo "  Omit '-z localhost:2181' from the above command if you have defined ZK_HOST in solr.in.sh."
    echo ""
    echo "Pass -help or -h after any COMMAND to see command-specific usage information,"
    echo "  such as:    ./solr start -help or ./solr stop -h"
    echo ""
  elif [[ "$CMD" == "start" || "$CMD" == "restart" ]]; then
    echo ""
    echo "Usage: solr $CMD [-f] [-c] [-h hostname] [-p port] [-d directory] [-z zkHost] [-m memory] [-e example] [-s solr.solr.home] [-t solr.data.home] [-a \"additional-options\"] [-V]"
    echo ""
    echo "  -f                    Start Solr in foreground; default starts Solr in the background"
    echo "                          and sends stdout / stderr to solr-PORT-console.log"
    echo ""
    echo "  -c or -cloud          Start Solr in SolrCloud mode; if -z not supplied and ZK_HOST not defined in"
    echo "                          solr.in.sh, an embedded ZooKeeper instance is started on Solr port+1000,"
    echo "                          such as 9983 if Solr is bound to 8983"
    echo ""
    echo "  -h/-host <host>       Specify the hostname for this Solr instance"
    echo ""
    echo "  -p <port>             Specify the port to start the Solr HTTP listener on; default is 8983"
    echo "                          The specified port (SOLR_PORT) will also be used to determine the stop port"
    echo "                          STOP_PORT=(\$SOLR_PORT-1000) and JMX RMI listen port RMI_PORT=(\$SOLR_PORT+10000). "
    echo "                          For instance, if you set -p 8985, then the STOP_PORT=7985 and RMI_PORT=18985"
    echo ""
    echo "  -d <dir>              Specify the Solr server directory; defaults to server"
    echo ""
    echo "  -z/-zkHost <zkHost>   Zookeeper connection string; only used when running in SolrCloud mode using -c"
    echo "                          If neither ZK_HOST is defined in solr.in.sh nor the -z parameter is specified,"
    echo "                          an embedded ZooKeeper instance will be launched."
    echo "                          Set the ZK_CREATE_CHROOT environment variable to true if your ZK host has a chroot path, and you want to create it automatically."
    echo ""
    echo "  -m <memory>           Sets the min (-Xms) and max (-Xmx) heap size for the JVM, such as: -m 4g"
    echo "                          results in: -Xms4g -Xmx4g; by default, this script sets the heap size to 512m"
    echo ""
    echo "  -s <dir>              Sets the solr.solr.home system property; Solr will create core directories under"
    echo "                          this directory. This allows you to run multiple Solr instances on the same host"
    echo "                          while reusing the same server directory set using the -d parameter. If set, the"
    echo "                          specified directory should contain a solr.xml file, unless solr.xml exists in Zookeeper."
    echo "                          This parameter is ignored when running examples (-e), as the solr.solr.home depends"
    echo "                          on which example is run. The default value is server/solr. If passed relative dir,"
    echo "                          validation with current dir will be done, before trying default server/<dir>"
    echo ""
    echo "  -t <dir>              Sets the solr.data.home system property, where Solr will store index data in <instance_dir>/data subdirectories."
    echo "                          If not set, Solr uses solr.solr.home for config and data."
    echo ""
    echo "  -e <example>          Name of the example to run; available examples:"
    echo "      cloud:              SolrCloud example"
    echo "      techproducts:       Comprehensive example illustrating many of Solr's core capabilities"
    echo "      schemaless:         Schema-less example (schema is inferred from data during indexing)"
    echo "      films:              Example of starting with _default configset and adding explicit fields dynamically"
    echo ""
    echo "  -a <jvmParams>        Additional parameters to pass to the JVM when starting Solr, such as to setup"
    echo "                          Java debug options. For example, to enable a Java debugger to attach to the Solr JVM"
    echo "                          you could pass: -a \"-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=18983\""
    echo "                          In most cases, you should wrap the additional parameters in double quotes."
    echo ""
    echo "  -j <jettyParams>      Additional parameters to pass to Jetty when starting Solr."
    echo "                          For example, to add configuration folder that jetty should read"
    echo "                          you could pass: -j \"--include-jetty-dir=/etc/jetty/custom/server/\""
    echo "                          In most cases, you should wrap the additional parameters in double quotes."
    echo ""
    echo "  -noprompt             Don't prompt for input; accept all defaults when running examples that accept user input"
    echo ""
    echo "  -force                If attempting to start Solr as the root user, the script will exit with a warning that running Solr as \"root\" can cause problems."
    echo "                          It is possible to override this warning with the '-force' parameter."
    echo ""
    echo "  -v and -q             Verbose (-v) or quiet (-q) logging. Sets default log level of Solr to DEBUG or WARN instead of INFO"
    echo ""
    echo "  -V/-verbose           Verbose messages from this script"
    echo ""
  elif [ "$CMD" == "stop" ]; then
    echo ""
    echo "Usage: solr stop [-k key] [-p port] [-V]"
    echo ""
    echo "  -k <key>      Stop key; default is solrrocks"
    echo ""
    echo "  -p <port>     Specify the port the Solr HTTP listener is bound to"
    echo ""
    echo "  -all          Find and stop all running Solr servers on this host"
    echo ""
    echo "  -V/-verbose   Verbose messages from this script"
    echo ""
    echo "  NOTE: To see if any Solr servers are running, do: solr status"
    echo ""
  elif [ "$CMD" == "healthcheck" ]; then
    echo ""
    echo "Usage: solr healthcheck [-c collection] [-z zkHost] [-V]"
    echo ""
    echo "Can be run from remote (non-Solr) hosts, as long as a proper ZooKeeper connection is provided"
    echo ""
    echo "  -c <collection>         Collection to run healthcheck against."
    echo ""
    echo "  -z or -zkHost <zkHost>  Zookeeper connection string; unnecessary if ZK_HOST is defined in solr.in.sh;"
    echo "                            otherwise, default is localhost:9983"
    echo ""
    echo "  -V/-verbose             Enable more verbose output for this script."
    echo ""
  elif [ "$CMD" == "status" ]; then
    echo ""
    echo "Usage: solr status"
    echo ""
    echo "  This command will show the status of all running Solr servers."
    echo "  It can only detect those Solr servers running on the current host."
    echo ""
  elif [ "$CMD" == "create" ]; then
    echo ""
    echo "Usage: solr create [-c name] [-d confdir] [-n configName] [-shards #] [-replicationFactor #] [-p port] [-V]"
    echo ""
    echo "  Create a core or collection depending on whether Solr is running in standalone (core) or SolrCloud"
    echo "  mode (collection). In other words, this action detects which mode Solr is running in, and then takes"
    echo "  the appropriate action (either create_core or create_collection). For detailed usage instructions, do:"
    echo ""
    echo "    bin/solr create_core -help"
    echo ""
    echo "       or"
    echo ""
    echo "    bin/solr create_collection -help"
    echo ""
  elif [ "$CMD" == "delete" ]; then
    echo ""
    echo "Usage: solr delete [-c name] [-deleteConfig true|false] [-p port] [-V]"
    echo ""
    echo "  Deletes a core or collection depending on whether Solr is running in standalone (core) or SolrCloud"
    echo "  mode (collection). If you're deleting a collection in SolrCloud mode, the default behavior is to also"
    echo "  delete the configuration directory from Zookeeper so long as it is not being used by another collection."
    echo "  You can override this behavior by passing -deleteConfig false when running this command."
    echo ""
    echo "  Can be run on remote (non-Solr) hosts, as long as a valid SOLR_HOST is provided in solr.in.sh"
    echo ""
    echo "  -c <name>               Name of the core / collection to delete"
    echo ""
    echo "  -deleteConfig <boolean> Delete the configuration directory from Zookeeper; default is true"
    echo ""
    echo "  -p or -port <port>      Port of a local Solr instance where you want to delete the core/collection"
    echo "                            If not specified, the script will search the local system for a running"
    echo "                            Solr instance and will use the port of the first server it finds."
    echo ""
    echo "  -V/-verbose             Enable more verbose output for this script."
    echo ""
  elif [ "$CMD" == "create_core" ]; then
    echo ""
    echo "Usage: solr create_core [-c core] [-d confdir] [-p port] [-V]"
    echo ""
    echo "When a configSet is used, this can be run from remote (non-Solr) hosts.  If pointing at a non-configSet directory, this"
    echo "must be run from the host that you wish to create the core on"
    echo ""
    echo "  -c <core>           Name of core to create"
    echo ""
    echo "  -d <confdir>        Configuration directory to copy when creating the new core, built-in options are:"
    echo ""
    echo "      _default: Minimal configuration, which supports enabling/disabling field-guessing support"
    echo "      sample_techproducts_configs: Example configuration with many optional features enabled to"
    echo "         demonstrate the full power of Solr"
    echo ""
    echo "      If not specified, default is: _default"
    echo ""
    echo "      Alternatively, you can pass the path to your own configuration directory instead of using"
    echo "      one of the built-in configurations, such as: bin/solr create_core -c mycore -d /tmp/myconfig"
    echo ""
    echo "  -p or -port <port>  Port of a local Solr instance where you want to create the new core"
    echo "                        If not specified, the script will search the local system for a running"
    echo "                        Solr instance and will use the port of the first server it finds."
    echo ""
    echo "  -force              If attempting to start Solr as the root user, the script will exit with a warning that running Solr as "root" can cause problems."
    echo "                        It is possible to override this warning with the `-force` parameter."
    echo ""
    echo "  -V/-verbose   Enable more verbose output for this script"
    echo ""
  elif [ "$CMD" == "create_collection" ]; then
    echo ""
    echo "Usage: solr create_collection [-c collection] [-d confdir] [-n configName] [-shards #] [-replicationFactor #] [-p port] [-V]"
    echo ""
    echo "Can be run from remote (non-Solr) hosts, as long as a valid SOLR_HOST is provided in solr.in.sh"
    echo "  -c <collection>               Name of collection to create"
    echo ""
    echo "  -d <confdir>                  Configuration directory to copy when creating the new collection, built-in options are:"
    echo ""
    echo "        _default: Minimal configuration, which supports enabling/disabling field-guessing support"
    echo "          sample_techproducts_configs: Example configuration with many optional features enabled to"
    echo "          demonstrate the full power of Solr"
    echo ""
    echo "        If not specified, default is: _default"
    echo ""
    echo "        Alternatively, you can pass the path to your own configuration directory instead of using"
    echo "        one of the built-in configurations, such as: bin/solr create_collection -c mycoll -d /tmp/myconfig"
    echo ""
    echo "        By default the script will upload the specified confdir directory into Zookeeper using the same"
    echo "        name as the collection (-c) option. Alternatively, if you want to reuse an existing directory"
    echo "        or create a confdir in Zookeeper that can be shared by multiple collections, use the -n option"
    echo ""
    echo "  -n <configName>                 Name the configuration directory in Zookeeper; by default, the configuration"
    echo "                                    will be uploaded to Zookeeper using the collection name (-c), but if you want"
    echo "                                    to use an existing directory or override the name of the configuration in"
    echo "                                    Zookeeper, then use the -c option."
    echo ""
    echo "  -shards <#>                     Number of shards to split the collection into; default is 1"
    echo ""
    echo "  -replicationFactor or -rf <#>   Number of copies of each document in the collection, default is 1 (no replication)"
    echo ""
    echo "  -p or -port <port>              Port of a local Solr instance where you want to create the new collection"
    echo "                                    If not specified, the script will search the local system for a running"
    echo "                                    Solr instance and will use the port of the first server it finds."
    echo ""
    echo "  -force                          If attempting to start Solr as the root user, the script will exit with a warning that running Solr as "root" can cause problems."
    echo "                                    It is possible to override this warning with the `-force` parameter."
    echo ""
    echo "  -V/-verbose                     Enable more verbose output for this script."
    echo ""
  elif [ "$CMD" == "zk" ]; then
    print_short_zk_usage ""
    echo "         Can be run on remote (non-Solr) hosts, as long as valid ZK_HOST information is provided"
    echo "         Be sure to check the Solr logs in case of errors."
    echo ""
    echo "             -z zkHost          Optional Zookeeper connection string for all commands. If specified it"
    echo "                                  overrides the 'ZK_HOST=...'' defined in solr.in.sh."
    echo ""
    echo "             -V/-verbose        Enable more verbose output for this script."
    echo ""
    echo "         upconfig uploads a configset from the local machine to Zookeeper. (Backcompat: -upconfig)"
    echo ""
    echo "         downconfig downloads a configset from Zookeeper to the local machine. (Backcompat: -downconfig)"
    echo ""
    echo "             -n <configName>    Name of the configset in Zookeeper that will be the destination of"
    echo "                                  'upconfig' and the source for 'downconfig'."
    echo ""
    echo "             -d <confdir>       The local directory the configuration will be uploaded from for"
    echo "                                  'upconfig' or downloaded to for 'downconfig'. If 'confdir' is a child of"
    echo "                                  ...solr/server/solr/configsets' then the configs will be copied from/to"
    echo "                                  that directory. Otherwise it is interpreted as a simple local path."
    echo ""
    echo "         cp copies files or folders to/from Zookeeper or Zookeeper -> Zookeeper"
    echo ""
    echo "             -r       Recursively copy <src> to <dst>. Command will fail if <src> has children and "
    echo "                        -r is not specified. Optional"
    echo ""
    echo "             <src>, <dest> : [file:][/]path/to/local/file or zk:/path/to/zk/node"
    echo "                             NOTE: <src> and <dest> may both be Zookeeper resources prefixed by 'zk:'"
    echo "             When <src> is a zk resource, <dest> may be '.'"
    echo "             If <dest> ends with '/', then <dest> will be a local folder or parent znode and the last"
    echo "             element of the <src> path will be appended unless <src> also ends in a slash. "
    echo "             <dest> may be zk:, which may be useful when using the cp -r form to backup/restore "
    echo "             the entire zk state."
    echo "             You must enclose local paths that end in a wildcard in quotes or just"
    echo "             end the local path in a slash. That is,"
    echo "             'bin/solr zk cp -r /some/dir/ zk:/ -z localhost:2181' is equivalent to"
    echo "             'bin/solr zk cp -r \"/some/dir/*\" zk:/ -z localhost:2181'"
    echo "             but 'bin/solr zk cp -r /some/dir/* zk:/ -z localhost:2181' will throw an error"
    echo ""
    echo "             here's an example of backup/restore for a ZK configuration:"
    echo "             to copy to local: 'bin/solr zk cp -r zk:/ /some/dir -z localhost:2181'"
    echo "             to restore to ZK: 'bin/solr zk cp -r /some/dir/ zk:/ -z localhost:2181'"
    echo ""
    echo "             The 'file:' prefix is stripped, thus 'file:/wherever' specifies an absolute local path and"
    echo "             'file:somewhere' specifies a relative local path. All paths on Zookeeper are absolute."
    echo ""
    echo "             Zookeeper nodes CAN have data, so moving a single file to a parent znode"
    echo "             will overlay the data on the parent Znode so specifying the trailing slash"
    echo "             can be important."
    echo ""
    echo "             Wildcards are supported when copying from local, trailing only and must be quoted."
    echo ""
    echo "         rm deletes files or folders on Zookeeper"
    echo ""
    echo "             -r       Recursively delete if <path> is a directory. Command will fail if <path>"
    echo "                        has children and -r is not specified. Optional"
    echo "             <path> : [zk:]/path/to/zk/node. <path> may not be the root ('/')"
    echo ""
    echo "         mv moves (renames) znodes on Zookeeper"
    echo ""
    echo "             <src>, <dest> : Zookeeper nodes, the 'zk:' prefix is optional."
    echo "             If <dest> ends with '/', then <dest> will be a parent znode"
    echo "             and the last element of the <src> path will be appended."
    echo "             Zookeeper nodes CAN have data, so moving a single file to a parent znode"
    echo "             will overlay the data on the parent Znode so specifying the trailing slash"
    echo "             is important."
    echo ""
    echo "         ls lists the znodes on Zookeeper"
    echo ""
    echo "             -r       Recursively descends the path listing all znodes. Optional"
    echo "             <path>:  The Zookeeper path to use as the root."
    echo ""
    echo "             Only the node names are listed, not data"
    echo ""
    echo "         mkroot makes a znode in Zookeeper with no data. Can be used to make a path of arbitrary"
    echo "             depth but primarily intended to create a 'chroot'."
    echo ""
    echo "             <path>:  The Zookeeper path to create. Leading slash is assumed if not present."
    echo "                        Intermediate nodes are created as needed if not present."
    echo ""
  elif [ "$CMD" == "auth" ]; then
    echo ""
    echo "Usage: solr auth enable [-type basicAuth] -credentials user:pass [-blockUnknown <true|false>] [-updateIncludeFileOnly <true|false>] [-V]"
    echo "       solr auth enable [-type basicAuth] -prompt <true|false> [-blockUnknown <true|false>] [-updateIncludeFileOnly <true|false>] [-V]"
    echo "       solr auth enable -type kerberos -config \"<kerberos configs>\" [-updateIncludeFileOnly <true|false>] [-V]"
    echo "       solr auth disable [-updateIncludeFileOnly <true|false>] [-V]"
    echo ""
    echo "  Updates or enables/disables authentication.  Must be run on the machine hosting Solr."
    echo ""
    echo "  -type or -t <type>                     The authentication mechanism (basicAuth or kerberos) to enable. Defaults to 'basicAuth'."
    echo ""
    echo "  -credentials <user:pass>               The username and password of the initial user. Applicable for basicAuth only."
    echo "                                          Note: only one of -prompt or -credentials must be provided"
    echo ""
    echo "  -config \"<configs>\"                  Configuration parameters (Solr startup parameters). Required and applicable only for Kerberos"
    echo ""
    echo "  -solrIncludeFile <includeFilePath>     Specify the full path to the include file in the environment."
    echo "                                          If not specified this script looks for an include file named solr.in.sh to set environment variables. "
    echo "                                          Specifically,the following locations are searched in this order:"
    echo "                                              <script location>/."
    echo "                                              $HOME/.solr.in.sh"
    echo "                                              /usr/share/solr"
    echo "                                              /usr/local/share/solr"
    echo "                                              /etc/default"
    echo "                                              /var/solr"
    echo "                                              /opt/solr"
    echo ""
    echo "  -prompt <true|false>                   Prompts the user to provide the credentials. Applicable for basicAuth only."
    echo "                                          Note: only one of -prompt or -credentials must be provided"
    echo ""
    echo "  -blockUnknown <true|false>             When true, this blocks out access to unauthenticated users. When not provided,"
    echo "                                          this defaults to false (i.e. unauthenticated users can access all endpoints, except the"
    echo "                                          operations like collection-edit, security-edit, core-admin-edit etc.). Check the reference"
    echo "                                          guide for Basic Authentication for more details. Applicable for basicAuth only."
    echo ""
    echo "  -updateIncludeFileOnly <true|false>    Only update the solr.in.sh or solr.in.cmd file, and skip actual enabling/disabling"
    echo "                                          authentication (i.e. don't update security.json)"
    echo ""
    echo "  -z or -zkHost <zkHost>                 Zookeeper connection string. Unnecessary if ZK_HOST is defined in solr.in.sh."
    echo ""
    echo "  -d or -dir <dir>                       Specify the Solr server directory"
    echo ""
    echo "  -s or -solr.home <dir>                 Specify the Solr home directory. This is where any credentials or authentication"
    echo "                                          configuration files (e.g. basicAuth.conf) would be placed."
    echo ""
    echo "  -V/-verbose                            Enable more verbose output for this script."
    echo ""
  elif [ "$CMD" == "package" ]; then
    echo ""
    run_tool package "help"
  fi
} # end print_usage

function print_short_zk_usage() {

  if [ "$1" != "" ]; then
    echo -e "\nERROR: $1\n"
  fi

  echo "  Usage: solr zk upconfig|downconfig -d <confdir> -n <configName> [-z zkHost]"
  echo "         solr zk cp [-r] <src> <dest> [-z zkHost]"
  echo "         solr zk rm [-r] <path> [-z zkHost]"
  echo "         solr zk mv <src> <dest> [-z zkHost]"
  echo "         solr zk ls [-r] <path> [-z zkHost]"
  echo "         solr zk mkroot <path> [-z zkHost]"
  echo ""

  if [ "$1" == "" ]; then
    echo "Type bin/solr zk -help for full usage help"
  else
    exit 1
  fi
}

# used to show the script is still alive when waiting on work to complete
function spinner() {
  local pid=$1
  local delay=0.5
  # shellcheck disable=SC1003
  local spinstr='|/-\'
  while ps -o pid='' -p "$pid" &> /dev/null ; do
      local temp=${spinstr#?}
      printf " [%c]  " "$spinstr"
      local spinstr=$temp${spinstr%"$temp"}
      sleep $delay
      printf "\b\b\b\b\b\b"
  done
  printf "    \b\b\b\b"
}

# given a port, find the pid for a Solr process
function solr_pid_by_port() {
  THE_PORT="$1"
  if [ -e "$SOLR_PID_DIR/solr-$THE_PORT.pid" ]; then
    PID=$(cat "$SOLR_PID_DIR/solr-$THE_PORT.pid")
    CHECK_PID=$(ps -o pid='' -p "$PID" | tr -d ' ')
    if [ -n "$CHECK_PID" ]; then
      echo "$PID"
    fi
  fi
}

# extract the value of the -Djetty.port parameter from a running Solr process
function jetty_port() {
  SOLR_PID="$1"
  SOLR_PROC=$(ps -fww -p "$SOLR_PID" | grep start\.jar | grep jetty\.port)
  IFS=' ' read -a proc_args <<< "$SOLR_PROC"
  for arg in "${proc_args[@]}"
    do
      IFS='=' read -a pair <<< "$arg"
      if [ "${pair[0]}" == "-Djetty.port" ]; then
        local jetty_port="${pair[1]}"
        break
      fi
    done
  echo "$jetty_port"
} # end jetty_port func

# run a Solr command-line tool using the SolrCLI class;
# useful for doing cross-platform work from the command-line using Java
function run_tool() {

  # shellcheck disable=SC2086
  "$JAVA" $SOLR_SSL_OPTS $AUTHC_OPTS ${SOLR_ZK_CREDS_AND_ACLS:-} ${SOLR_TOOL_OPTS:-} -Dsolr.install.dir="$SOLR_TIP" \
    -Dlog4j.configurationFile="$DEFAULT_SERVER_DIR/resources/log4j2-console.xml" \
    -classpath "$DEFAULT_SERVER_DIR/solr-webapp/webapp/WEB-INF/lib/*:$DEFAULT_SERVER_DIR/lib/ext/*:$DEFAULT_SERVER_DIR/lib/*" \
    org.apache.solr.cli.SolrCLI "$@"

  return $?
} # end run_tool function

# get status about any Solr nodes running on this host
function get_status() {
  # first, see if Solr is running
  numSolrs=$(find "$SOLR_PID_DIR" -name "solr-*.pid" -type f | wc -l | tr -d ' ')
  if [ "$numSolrs" != "0" ]; then
    echo -e "\nFound $numSolrs Solr nodes: "
    while read PIDF
      do
        ID=$(cat "$PIDF")
        port=$(jetty_port "$ID")
        if [ "$port" != "" ]; then
          echo -e "\nSolr process $ID running on port $port"
          run_tool status -solr "$SOLR_URL_SCHEME://$SOLR_TOOL_HOST:$port/solr"
          echo ""
        else
          echo -e "\nSolr process $ID from $PIDF not found."
        fi
    done < <(find "$SOLR_PID_DIR" -name "solr-*.pid" -type f)
  else
    # no pid files but check using ps just to be sure
    numSolrs=$(ps auxww | grep start\.jar | grep solr\.solr\.home | grep -v grep | wc -l | sed -e 's/^[ \t]*//')
    if [ "$numSolrs" != "0" ]; then
      echo -e "\nFound $numSolrs Solr nodes: "
      PROCESSES=$(ps auxww | grep start\.jar | grep solr\.solr\.home | grep -v grep | awk '{print $2}' | sort -r)
      for ID in $PROCESSES
        do
          port=$(jetty_port "$ID")
          if [ "$port" != "" ]; then
            echo ""
            echo "Solr process $ID running on port $port"
            run_tool status -solr "$SOLR_URL_SCHEME://$SOLR_TOOL_HOST:$port/solr"
            echo ""
          fi
      done
    else
      echo -e "\nNo Solr nodes are running.\n"
    fi
  fi

} # end get_status

function run_package() {
  runningSolrUrl=""

  numSolrs=$(find "$SOLR_PID_DIR" -name "solr-*.pid" -type f | wc -l | tr -d ' ')
  if [ "$numSolrs" != "0" ]; then
    #echo -e "\nFound $numSolrs Solr nodes: "
    while read PIDF
      do
        ID=$(cat "$PIDF")
        port=$(jetty_port "$ID")
        if [ "$port" != "" ]; then
          #echo -e "\nSolr process $ID running on port $port"
          runningSolrUrl="$SOLR_URL_SCHEME://$SOLR_TOOL_HOST:$port/solr"
          break
          CODE=$?
          echo ""
        else
          echo -e "\nSolr process $ID from $PIDF not found."
          CODE=1
        fi
    done < <(find "$SOLR_PID_DIR" -name "solr-*.pid" -type f)
  else
    # no pid files but check using ps just to be sure
    numSolrs=$(ps auxww | grep start\.jar | grep solr\.solr\.home | grep -v grep | wc -l | sed -e 's/^[ \t]*//')
    if [ "$numSolrs" != "0" ]; then
      echo -e "\nFound $numSolrs Solr nodes: "
      PROCESSES=$(ps auxww | grep start\.jar | grep solr\.solr\.home | grep -v grep | awk '{print $2}' | sort -r)
      for ID in $PROCESSES
        do
          port=$(jetty_port "$ID")
          if [ "$port" != "" ]; then
            echo ""
            echo "Solr process $ID running on port $port"
            runningSolrUrl="$SOLR_URL_SCHEME://$SOLR_TOOL_HOST:$port/solr"
            break
            CODE=$?
            echo ""
          fi
      done
    else
      echo -e "\nNo Solr nodes are running.\n"
      exit 1
      CODE=3
    fi
  fi

  run_tool package -solrUrl "$runningSolrUrl" "$@"
  #exit $?
}

# tries to gracefully stop Solr using the Jetty
# stop command and if that fails, then uses kill -9
# (will attempt to thread dump before killing)
function stop_solr() {

  DIR="$1"
  SOLR_PORT="$2"
  THIS_STOP_PORT="${STOP_PORT:-$((SOLR_PORT - 1000))}"
  STOP_KEY="$3"
  SOLR_PID="$4"

  if [ -n "$SOLR_PID"  ]; then
    echo -e "Sending stop command to Solr running on port $SOLR_PORT ... waiting up to $SOLR_STOP_WAIT seconds to allow Jetty process $SOLR_PID to stop gracefully."
    # shellcheck disable=SC2086
    "$JAVA" $SOLR_SSL_OPTS $AUTHC_OPTS ${SOLR_TOOL_OPTS:-} -jar "$DIR/start.jar" "STOP.PORT=$THIS_STOP_PORT" "STOP.KEY=$STOP_KEY" --stop || true
      (loops=0
      while true
      do
        # Check if a process is running with the specified PID.
        # -o stat will output the STAT, where Z indicates a zombie
        # stat='' removes the header (--no-headers isn't supported on all platforms)
        # Note the space after '$('. It is needed to avoid confusion with special bash eval syntax
        STAT=$( (ps -o stat='' -p "$SOLR_PID" || :) | tr -d ' ')
        if [[ "${STAT:-Z}" != "Z" ]]; then
          slept=$((loops * 2))
          if [ $slept -lt $SOLR_STOP_WAIT ]; then
            sleep 2
            loops=$((loops+1))
          else
            exit # subshell!
          fi
        else
          exit # subshell!
        fi
      done) &
    spinner $!
    rm -f "$SOLR_PID_DIR/solr-$SOLR_PORT.pid"
  else
    echo -e "No Solr nodes found to stop."
    exit 0
  fi

  # Note the space after '$('. It is needed to avoid confusion with special bash eval syntax
  STAT=$( (ps -o stat='' -p "$SOLR_PID" || :) | tr -d ' ')
  if [[ "${STAT:-Z}" != "Z" ]]; then
    if [ -n "${JSTACK:-}" ]; then
      echo -e "Solr process $SOLR_PID is still running; jstacking it now."
      $JSTACK "$SOLR_PID"
    elif [ "$JATTACH" != "" ]; then
      echo -e "Solr process $SOLR_PID is still running; jattach threaddumping it now."
      $JATTACH "$SOLR_PID" threaddump
    fi
    echo -e "Solr process $SOLR_PID is still running; forcefully killing it now."
    kill -9 "$SOLR_PID"
    echo "Killed process $SOLR_PID"
    rm -f "$SOLR_PID_DIR/solr-$SOLR_PORT.pid"
    sleep 10
  fi

  # Note the space after '$('. It is needed to avoid confusion with special bash eval syntax
  STAT=$( (ps -o stat='' -p "$SOLR_PID" || :) | tr -d ' ')
  if [ "${STAT:-}" == "Z" ]; then
    # This can happen if, for example, you are running Solr inside a docker container with multiple processes
    # rather than running it is as the only service. The --init flag on docker avoids that particular problem.
    echo -e "Solr process $SOLR_PID has terminated abnormally. Solr has exited but a zombie process entry remains."
    exit 1
  elif [ -n "${STAT:-}" ]; then
    echo "ERROR: Failed to kill previous Solr Java process $SOLR_PID ... script fails."
    exit 1
  fi
} # end stop_solr

if [ $# -eq 1 ]; then
  case $1 in
    -help|-h)
        print_usage ""
        exit
    ;;
  esac
fi

if [ $# -gt 0 ]; then
  # if first arg starts with a dash (and it's not -help or -info),
  # then assume they are starting Solr, such as: solr -f
  if [[ $1 == -* ]]; then
    SCRIPT_CMD="start"
  else
    SCRIPT_CMD="$1"
    shift
  fi
else
  # no args - just show usage and exit
  print_usage ""
  exit
fi

if [ "$SCRIPT_CMD" == "status" ]; then
  if [ $# -gt 0 ]; then
    while true; do
      case "$1" in
          -help|-h)
              print_usage "$SCRIPT_CMD"
              exit 0
          ;;
          --)
              shift
              break
          ;;
          *)
              if [ "$1" != "" ]; then
                print_usage "$SCRIPT_CMD" "Unrecognized or misplaced argument: $1!"
                exit 1
              else
                break # out-of-args, stop looping
              fi
          ;;
      esac
    done
  fi
  get_status
  exit
fi

# assert tool
if [ "$SCRIPT_CMD" == "assert" ]; then
  run_tool assert "$@"
  exit $?
fi

# run a healthcheck and exit if requested
if [ "$SCRIPT_CMD" == "healthcheck" ]; then

  VERBOSE=""

  if [ $# -gt 0 ]; then
    while true; do
      case "$1" in
          -c|-collection)
              if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
                print_usage "$SCRIPT_CMD" "Collection name is required when using the $1 option!"
                exit 1
              fi
              HEALTHCHECK_COLLECTION="$2"
              shift 2
          ;;
          -z|-zkhost|-zkHost)
              if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
                print_usage "$SCRIPT_CMD" "ZooKeeper connection string is required when using the $1 option!"
                exit 1
              fi
              ZK_HOST="$2"
              shift 2
          ;;
          -help|-h)
              print_usage "$SCRIPT_CMD"
              exit 0
          ;;
          -V|-verbose)
              VERBOSE="-verbose"
              shift
          ;;
          --)
              shift
              break
          ;;
          *)
              if [ "$1" != "" ]; then
                print_usage "$SCRIPT_CMD" "Unrecognized or misplaced argument: $1!"
                exit 1
              else
                break # out-of-args, stop looping
              fi
          ;;
      esac
    done
  fi

  if [ -z "$ZK_HOST" ]; then
    ZK_HOST=localhost:9983
  fi

  if [ -z "$HEALTHCHECK_COLLECTION" ]; then
    echo "collection parameter is required!"
    print_usage "healthcheck"
    exit 1
  fi

  run_tool healthcheck -zkHost "$ZK_HOST" -collection "$HEALTHCHECK_COLLECTION" $VERBOSE

  exit $?
fi

if [[ "$SCRIPT_CMD" == "config" ]]; then
  CONFIG_PARAMS=()

  if [ $# -gt 0 ]; then
    while true; do
      case "$1" in
          -z|-zkhost|-zkHost)
              if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
                print_usage "$SCRIPT_CMD" "ZooKeeper connection string is required when using the $1 option!"
                exit 1
              fi
              ZK_HOST="$2"
              shift 2
          ;;
          -s|-scheme)
              if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
                print_usage "$SCRIPT_CMD" "URL scheme is required when using the $1 option!"
                exit 1
              fi
              SOLR_URL_SCHEME="$2"
              shift 2
          ;;
          *)  # Pass through all other params
              if [ "$1" != "" ]; then
                CONFIG_PARAMS+=($1)
                shift
              else
                break
              fi
          ;;
      esac
    done
  fi
  if [[ -n "$ZK_HOST" ]]; then
    CONFIG_PARAMS+=("-z" "$ZK_HOST")
  fi
  if [[ -n "$SOLR_URL_SCHEME" ]]; then
    CONFIG_PARAMS+=("-scheme" "$SOLR_URL_SCHEME")
  fi
  run_tool config "${CONFIG_PARAMS[@]}"
  exit $?
fi

# create a core or collection
if [[ "$SCRIPT_CMD" == "create" || "$SCRIPT_CMD" == "create_core" || "$SCRIPT_CMD" == "create_collection" ]]; then

  CREATE_NUM_SHARDS=1
  CREATE_REPFACT=1
  FORCE=false
  VERBOSE=""

  if [ $# -gt 0 ]; then
    while true; do
      case "${1:-}" in
          -c|-core|-collection)
              if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
                print_usage "$SCRIPT_CMD" "name is required when using the $1 option!"
                exit 1
              fi
              CREATE_NAME="$2"
              shift 2
          ;;
          -n|-confname)
              if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
                print_usage "$SCRIPT_CMD" "Configuration name is required when using the $1 option!"
                exit 1
              fi
              CREATE_CONFNAME="$2"
              shift 2
          ;;
          -d|-confdir)
              if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
                print_usage "$SCRIPT_CMD" "Configuration directory is required when using the $1 option!"
                exit 1
              fi
              CREATE_CONFDIR="$2"
              shift 2
          ;;
          -s|-shards)
              if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
                print_usage "$SCRIPT_CMD" "Shard count is required when using the $1 option!"
                exit 1
              fi
              CREATE_NUM_SHARDS="$2"
              shift 2
          ;;
          -rf|-replicationFactor)
              if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
                print_usage "$SCRIPT_CMD" "Replication factor is required when using the $1 option!"
                exit 1
              fi
              CREATE_REPFACT="$2"
              shift 2
          ;;
          -p|-port)
              if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
                print_usage "$SCRIPT_CMD" "Solr port is required when using the $1 option!"
                exit 1
              fi
              CREATE_PORT="$2"
              shift 2
          ;;
          -V|-verbose)
              VERBOSE="-verbose"
              shift
          ;;
          -force)
              FORCE=true
              shift
          ;;
          -help|-h)
              print_usage "$SCRIPT_CMD"
              exit 0
          ;;
          --)
              shift
              break
          ;;
          *)
              if [ -n "${1:-}" ]; then
                print_usage "$SCRIPT_CMD" "Unrecognized or misplaced argument: $1!"
                exit 1
              else
                break # out-of-args, stop looping
              fi
          ;;
      esac
    done
  fi

  : "${CREATE_CONFDIR:=_default}"

  # validate the confdir arg (if provided)
  if [[ ! -d "$SOLR_TIP/server/solr/configsets/$CREATE_CONFDIR" && ! -d "$CREATE_CONFDIR" ]]; then
    echo -e "\nSpecified configuration directory $CREATE_CONFDIR not found!\n"
    exit 1
  fi

  if [ -z "${CREATE_NAME:-}" ]; then
    echo "Name (-c) argument is required!"
    print_usage "$SCRIPT_CMD"
    exit 1
  fi

  if [ -z "${CREATE_PORT:-}" ]; then
    for ID in $(ps auxww | grep java | grep start\.jar | awk '{print $2}' | sort -r)
      do
        port=$(jetty_port "$ID")
        if [ "$port" != "" ]; then
          CREATE_PORT=$port
          break
        fi
    done
  fi

  if [ -z "${CREATE_PORT:-}" ]; then
    echo "Failed to determine the port of a local Solr instance, cannot create $CREATE_NAME!"
    exit 1
  fi

  if [[ "$CREATE_CONFDIR" == "_default" ]] && [[ "${CREATE_CONFNAME:-_default}" == "_default" ]]; then
    echo "WARNING: Using _default configset with data driven schema functionality. NOT RECOMMENDED for production use."
    echo "         To turn off: bin/solr config -c $CREATE_NAME -p $CREATE_PORT -action set-user-property -property update.autoCreateFields -value false"
  fi

  if [[ $EUID -eq 0 ]] && [[ "$FORCE" == "false" ]] ; then
    echo "WARNING: Creating cores as the root user can cause Solr to fail and is not advisable. Exiting."
    echo "         If you started Solr as root (not advisable either), force core creation by adding argument -force"
    exit 1
  fi
  if [ "$SCRIPT_CMD" == "create_core" ]; then
    run_tool create_core -name "$CREATE_NAME" -solrUrl "$SOLR_URL_SCHEME://$SOLR_TOOL_HOST:$CREATE_PORT/solr" \
      -confdir "$CREATE_CONFDIR" -configsetsDir "$SOLR_TIP/server/solr/configsets" \
      $VERBOSE
    exit $?
  else
    # should we be passing confname if it is unset?
    run_tool "$SCRIPT_CMD" -name "$CREATE_NAME" -solrUrl "$SOLR_URL_SCHEME://$SOLR_TOOL_HOST:$CREATE_PORT/solr" \
      -shards "$CREATE_NUM_SHARDS" -replicationFactor "$CREATE_REPFACT" \
      -confname "${CREATE_CONFNAME:-}" -confdir "$CREATE_CONFDIR" \
      -configsetsDir "$SOLR_TIP/server/solr/configsets" \
      $VERBOSE
    exit $?
  fi
fi

# delete a core or collection
if [[ "$SCRIPT_CMD" == "delete" ]]; then

  VERBOSE=""

  if [ $# -gt 0 ]; then
    while true; do
      case "${1:-}" in
          -c|-core|-collection)
              if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
                print_usage "$SCRIPT_CMD" "name is required when using the $1 option!"
                exit 1
              fi
              DELETE_NAME="$2"
              shift 2
          ;;
          -p|-port)
              if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
                print_usage "$SCRIPT_CMD" "Solr port is required when using the $1 option!"
                exit 1
              fi
              DELETE_PORT="$2"
              shift 2
          ;;
          -deleteConfig)
              if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
                print_usage "$SCRIPT_CMD" "true|false is required when using the $1 option!"
                exit 1
              fi
              DELETE_CONFIG="$2"
              shift 2
          ;;
          -V|-verbose)
              VERBOSE="-verbose"
              shift
          ;;
          -help|-h)
              print_usage "$SCRIPT_CMD"
              exit 0
          ;;
          --)
              shift
              break
          ;;
          *)
              if [ -n "${1:-}" ]; then
                print_usage "$SCRIPT_CMD" "Unrecognized or misplaced argument: $1!"
                exit 1
              else
                break # out-of-args, stop looping
              fi
          ;;
      esac
    done
  fi

  if [ -z "$DELETE_NAME" ]; then
    echo "Name (-c) argument is required!"
    print_usage "$SCRIPT_CMD"
    exit 1
  fi

  # If not defined, use the collection name for the name of the configuration in Zookeeper
  : "${DELETE_CONFIG:=true}"

  if [ -z "${DELETE_PORT:-}" ]; then
    for ID in $(ps auxww | grep java | grep start\.jar | awk '{print $2}' | sort -r)
      do
        port=$(jetty_port "$ID")
        if [ "$port" != "" ]; then
          DELETE_PORT=$port
          break
        fi
    done
  fi

  if [ -z "${DELETE_PORT:-}" ]; then
    echo "Failed to determine the port of a local Solr instance, cannot delete $DELETE_NAME!"
    exit 1
  fi

  run_tool delete -name "$DELETE_NAME" -deleteConfig "$DELETE_CONFIG" \
    -solrUrl "$SOLR_URL_SCHEME://$SOLR_TOOL_HOST:$DELETE_PORT/solr" \
    $VERBOSE
  exit $?
fi

# Prevent any zk subcommands from going through with out invoking zk command
if [[ "$SCRIPT_CMD" == "upconfig" || $SCRIPT_CMD == "downconfig" || $SCRIPT_CMD == "cp" || $SCRIPT_CMD == "rm" || $SCRIPT_CMD == "mv" || $SCRIPT_CMD == "ls" || $SCRIPT_CMD == "mkroot" ]]; then
  print_short_zk_usage "You must invoke this subcommand using the zk command.   bin/solr zk $SCRIPT_CMD."
  exit $?
fi

ZK_RECURSE=false
# Zookeeper file maintenance (upconfig, downconfig, files up/down etc.)
# It's a little clumsy to have the parsing go round and round for upconfig and downconfig, but that's
# necessary for back-compat
if [[ "$SCRIPT_CMD" == "zk" ]]; then

  VERBOSE=""

  if [ $# -gt 0 ]; then
    while true; do
      case "${1:-}" in
        -upconfig|upconfig|-downconfig|downconfig|cp|rm|mv|ls|mkroot)
            if [ "${1:0:1}" == "-" ]; then
              echo "The use of $1 is deprecated.   Please use ${1:1} instead."
              ZK_OP=${1:1}
            else
              ZK_OP=$1
            fi
            shift 1
        ;;
        -z|-zkhost|-zkHost)
            if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
              print_short_zk_usage "$SCRIPT_CMD" "ZooKeeper connection string is required when using the $1 option!"
            fi
            ZK_HOST="$2"
            shift 2
        ;;
        -n|-confname)
            if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
              print_short_zk_usage "$SCRIPT_CMD" "Configuration name is required when using the $1 option!"
            fi
            CONFIGSET_CONFNAME="$2"
            shift 2
        ;;
        -d|-confdir)
            if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
              print_short_zk_usage "$SCRIPT_CMD" "Configuration directory is required when using the $1 option!"
            fi
            CONFIGSET_CONFDIR="$2"
            shift 2
        ;;
        -r)
            ZK_RECURSE="true"
            shift
        ;;
        -V|-verbose)
            VERBOSE="-verbose"
            shift
        ;;
        -help|-h)
            print_usage "$SCRIPT_CMD"
            exit 0
        ;;
        --)
            shift
            break
        ;;
        *)  # Pick up <src> <dst> or <path> params for rm, ls, cp, mv, mkroot.
            if [ -z "${1:-}" ]; then
              break # out-of-args, stop looping
            fi
            if [ -z "${ZK_SRC:-}" ]; then
              ZK_SRC=$1
            else
              if [ -z "${ZK_DST:-}" ]; then
                ZK_DST=$1
              else
                print_short_zk_usage "Unrecognized or misplaced command $1. 'cp' with trailing asterisk requires quoting, see help text."
              fi
            fi
            shift
        ;;
      esac
    done
  fi

  if [ -z "$ZK_OP" ]; then
    print_short_zk_usage "Zookeeper operation (one of 'upconfig', 'downconfig', 'rm', 'mv', 'cp', 'ls', 'mkroot') is required!"
  fi

  if [ -z "$ZK_HOST" ]; then
    print_short_zk_usage "Zookeeper address (-z) argument is required or ZK_HOST must be specified in the solr.in.sh file."
  fi

  if [[ "$ZK_OP" == "upconfig" ||  "$ZK_OP" == "downconfig" ]]; then
    if [ -z "$CONFIGSET_CONFDIR" ]; then
      print_short_zk_usage "Local directory of the configset (-d) argument is required!"
    fi

    if [ -z "$CONFIGSET_CONFNAME" ]; then
      print_short_zk_usage "Configset name on Zookeeper (-n) argument is required!"
    fi
  fi

  if [[ "$ZK_OP" == "cp" || "$ZK_OP" == "mv" ]]; then
    if [[ -z "$ZK_SRC" || -z "$ZK_DST" ]]; then
      print_short_zk_usage "<source> and <destination> must be specified when using either the 'mv' or 'cp' commands."
    fi
    if [[ "$ZK_OP" == "cp" && "${ZK_SRC:0:3}" != "zk:" && "${ZK_DST:0:3}" != "zk:" ]]; then
      print_short_zk_usage "One of the source or destination paths must be prefixed by 'zk:' for the 'cp' command."
    fi
  fi

  if [[ "$ZK_OP" == "mkroot" ]]; then
    if [[ -z "$ZK_SRC" ]]; then
      print_short_zk_usage "<path> must be specified when using the 'mkroot' command."
    fi
  fi


  case "$ZK_OP" in
    upconfig)
      run_tool "$ZK_OP" -confname "$CONFIGSET_CONFNAME" -confdir "$CONFIGSET_CONFDIR" -zkHost "$ZK_HOST" -configsetsDir "$SOLR_TIP/server/solr/configsets" $VERBOSE
    ;;
    downconfig)
      run_tool "$ZK_OP" -confname "$CONFIGSET_CONFNAME" -confdir "$CONFIGSET_CONFDIR" -zkHost "$ZK_HOST" $VERBOSE
    ;;
    rm)
      if [ -z "$ZK_SRC" ]; then
        print_short_zk_usage "Zookeeper path to remove must be specified when using the 'rm' command"
      fi
      run_tool "$ZK_OP" -path "$ZK_SRC" -zkHost "$ZK_HOST" -recurse "$ZK_RECURSE" $VERBOSE
    ;;
    mv)
      run_tool "$ZK_OP" -src "$ZK_SRC" -dst "$ZK_DST" -zkHost "$ZK_HOST" $VERBOSE
    ;;
    cp)
      run_tool "$ZK_OP" -src "$ZK_SRC" -dst "$ZK_DST" -zkHost "$ZK_HOST" -recurse "$ZK_RECURSE" $VERBOSE
    ;;
    ls)
      if [ -z "$ZK_SRC" ]; then
        print_short_zk_usage "Zookeeper path to list must be specified when using the 'ls' command"
      fi
      run_tool "$ZK_OP" -path "$ZK_SRC" -recurse "$ZK_RECURSE" -zkHost "$ZK_HOST" $VERBOSE
    ;;
    mkroot)
      if [ -z "$ZK_SRC" ]; then
        print_short_zk_usage "Zookeeper path to list must be specified when using the 'mkroot' command"
      fi
      run_tool "$ZK_OP" -path "$ZK_SRC" -zkHost "$ZK_HOST" $VERBOSE
    ;;
    *)
      print_short_zk_usage "Unrecognized Zookeeper operation $ZK_OP"
    ;;
  esac

  exit $?
fi

if [[ "$SCRIPT_CMD" == "package" ]]; then
  if [ $# -gt 0 ]; then
    while true; do
      case "$1" in
          -help|-h)
              print_usage "$SCRIPT_CMD"
              exit 0
          ;;
          --)
              shift
              break
          ;;
          *)
              break # out-of-args, stop looping

          ;;
      esac
    done
  fi
  run_package "$@"
  exit $?
fi

if [[ "$SCRIPT_CMD" == "auth" ]]; then

  VERBOSE=""

  declare -a AUTH_PARAMS
  if [ $# -gt 0 ]; then
    while true; do
      case "${1:-}" in
        enable|disable)
            AUTH_OP=$1
            AUTH_PARAMS=("${AUTH_PARAMS[@]}" "$AUTH_OP")
            shift
        ;;
        -z|-zkhost|-zkHost)
            ZK_HOST="$2"
            AUTH_PARAMS=("${AUTH_PARAMS[@]}" "-zkHost" "$ZK_HOST")
            shift 2
        ;;
        -t|-type)
            AUTH_TYPE="$2"
            AUTH_PARAMS=("${AUTH_PARAMS[@]}" "-type" "$AUTH_TYPE")
            shift 2
        ;;
        -credentials)
            AUTH_CREDENTIALS="$2"
            AUTH_PARAMS=("${AUTH_PARAMS[@]}" "-credentials" "$AUTH_CREDENTIALS")
            shift 2
        ;;
        -config)
            AUTH_CONFIG="$(echo "$2"| base64)"
            AUTH_PARAMS=("${AUTH_PARAMS[@]}" "-config" "$AUTH_CONFIG")
            shift 2
        ;;
        -solrIncludeFile)
            SOLR_INCLUDE="$2"
            shift 2
        ;;
        -prompt)
            AUTH_PARAMS=("${AUTH_PARAMS[@]}" "-prompt" "$2")
            shift 2
        ;;
        -blockUnknown)
            AUTH_PARAMS=("${AUTH_PARAMS[@]}" "-blockUnknown" "$2")
            shift 2
        ;;
        -updateIncludeFileOnly)
            AUTH_PARAMS=("${AUTH_PARAMS[@]}" "-updateIncludeFileOnly" "$2")
            shift 2
        ;;
        -V|-verbose)
            VERBOSE="-verbose"
            shift
        ;;
        -d|-dir)
            if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
              print_usage "$SCRIPT_CMD" "Server directory is required when using the $1 option!"
              exit 1
            fi

            if [[ "$2" == "." || "$2" == "./" || "$2" == ".." || "$2" == "../" ]]; then
              SOLR_SERVER_DIR="$(pwd -P)/$2"
            else
              # see if the arg value is relative to the tip vs full path
              if [[ "$2" != /* ]] && [[ -d "$SOLR_TIP/$2" ]]; then
                SOLR_SERVER_DIR="$SOLR_TIP/$2"
              else
                SOLR_SERVER_DIR="$2"
              fi
            fi
            # resolve it to an absolute path
            SOLR_SERVER_DIR="$(cd "$SOLR_SERVER_DIR" || (echo "SOLR_SERVER_DIR not found" && exit 1); pwd)"
            shift 2
        ;;
        -s|-solr.home)
            if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
              print_usage "$SCRIPT_CMD" "Solr home directory is required when using the $1 option!"
              exit 1
            fi

            SOLR_HOME="$2"
            shift 2
        ;;
        -help|-h)
            print_usage "$SCRIPT_CMD"
            exit 0
        ;;
        --)
            shift
            break
        ;;
        *)
            shift
            break
        ;;
      esac
    done
  fi

  : "${SOLR_SERVER_DIR:=$DEFAULT_SERVER_DIR}"
  if [ ! -e "$SOLR_SERVER_DIR" ]; then
    echo -e "\nSolr server directory $SOLR_SERVER_DIR not found!\n"
    exit 1
  fi

  if [ -z "${SOLR_HOME:-}" ]; then
    SOLR_HOME="$SOLR_SERVER_DIR/solr"
  elif [[ $SOLR_HOME != /* ]]; then
    if [[ -d "$(pwd -P)/$SOLR_HOME" ]]; then
      SOLR_HOME="$(pwd -P)/$SOLR_HOME"
    elif [[ -d "$SOLR_SERVER_DIR/$SOLR_HOME" ]]; then
      SOLR_HOME="$SOLR_SERVER_DIR/$SOLR_HOME"
      SOLR_PID_DIR="$SOLR_HOME"
    fi
  fi

  if [ -z "$AUTH_OP" ]; then
    print_usage "$SCRIPT_CMD"
    exit 0
  fi

  AUTH_PARAMS=("${AUTH_PARAMS[@]}" "-solrIncludeFile" "$SOLR_INCLUDE")

  if [ -z "${AUTH_PORT:-}" ]; then
    for ID in $(ps auxww | grep java | grep start\.jar | awk '{print $2}' | sort -r)
      do
        port=$(jetty_port "$ID")
        if [ "$port" != "" ]; then
          AUTH_PORT=$port
          break
        fi
      done
  fi
  run_tool auth "${AUTH_PARAMS[@]}" -solrUrl "$SOLR_URL_SCHEME://$SOLR_TOOL_HOST:${AUTH_PORT:-8983}/solr" -authConfDir "$SOLR_HOME" $VERBOSE
  exit $?
fi


# verify the command given is supported
if [ "$SCRIPT_CMD" != "stop" ] && [ "$SCRIPT_CMD" != "start" ] && [ "$SCRIPT_CMD" != "restart" ] && [ "$SCRIPT_CMD" != "status" ]; then
  # handoff this command to the SolrCLI and let it handle the option parsing and validation
  run_tool "$SCRIPT_CMD" "$@"
  exit $?
fi

#Check current Ulimits for Open Files and Max Processes.  Warn if they are below the recommended values.

: "${SOLR_RECOMMENDED_MAX_PROCESSES:=65000}"
: "${SOLR_RECOMMENDED_OPEN_FILES:=65000}"

if [[ "${SOLR_ULIMIT_CHECKS:-}" != "false" ]]; then
  if [ "$SCRIPT_CMD" == "start" ] || [ "$SCRIPT_CMD" == "restart" ] || [ "$SCRIPT_CMD" == "status" ]; then
    if hash ulimit 2>/dev/null; then
       openFiles=$(ulimit -n)
       maxProcs=$(ulimit -u)
       virtualMemory=$(ulimit -v)
       maxMemory=$(ulimit -m)
       if [ "$openFiles" != "unlimited" ] && [ "$openFiles" -lt "$SOLR_RECOMMENDED_OPEN_FILES" ]; then
           echo "*** [WARN] *** Your open file limit is currently $openFiles.  "
           echo " It should be set to $SOLR_RECOMMENDED_OPEN_FILES to avoid operational disruption. "
           echo " If you no longer wish to see this warning, set SOLR_ULIMIT_CHECKS to false in your profile or solr.in.sh"
       fi

       if [ "$maxProcs" != "unlimited" ] && [ "$maxProcs" -lt "$SOLR_RECOMMENDED_MAX_PROCESSES" ]; then
           echo "*** [WARN] ***  Your Max Processes Limit is currently $maxProcs. "
           echo " It should be set to $SOLR_RECOMMENDED_MAX_PROCESSES to avoid operational disruption. "
           echo " If you no longer wish to see this warning, set SOLR_ULIMIT_CHECKS to false in your profile or solr.in.sh"
       fi
       if [ "$virtualMemory" != "unlimited" ]; then
           echo "*** [WARN] ***  Your Virtual Memory limit is $virtualMemory. "
           echo " It should be set to 'unlimited' to avoid operational disruption. "
           echo " If you no longer wish to see this warning, set SOLR_ULIMIT_CHECKS to false in your profile or solr.in.sh"
       fi
       if [ "$maxMemory" != "unlimited" ]; then
           echo "*** [WARN] ***  Your Max Memory Size limit is $maxMemory. "
           echo " It should be set to 'unlimited' to avoid operational disruption. "
           echo " If you no longer wish to see this warning, set SOLR_ULIMIT_CHECKS to false in your profile or solr.in.sh"
       fi

    else
      echo "Could not check ulimits for processes and open files, recommended values are"
      echo "     max processes:   $SOLR_RECOMMENDED_MAX_PROCESSES "
      echo "     open files:      $SOLR_RECOMMENDED_OPEN_FILES"
      echo "     virtual memory:  unlimited"
      echo "     max memory size: unlimited"
    fi
  fi
fi

# Run in foreground (default is to run in the background)
FG="false"
FORCE=false
SOLR_OPTS=(${SOLR_OPTS:-})
SCRIPT_SOLR_OPTS=()
PASS_TO_RUN_EXAMPLE=()

if [ $# -gt 0 ]; then
  while true; do
    case "${1:-}" in
        -c|-cloud)
            SOLR_MODE="solrcloud"
            PASS_TO_RUN_EXAMPLE+=("-c")
            shift
        ;;
        -d|-dir)
            if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
              print_usage "$SCRIPT_CMD" "Server directory is required when using the $1 option!"
              exit 1
            fi

            if [[ "$2" == "." || "$2" == "./" || "$2" == ".." || "$2" == "../" ]]; then
              SOLR_SERVER_DIR="$(pwd -P)/$2"
            else
              # see if the arg value is relative to the tip vs full path
              if [[ "$2" != /* ]] && [[ -d "$SOLR_TIP/$2" ]]; then
                SOLR_SERVER_DIR="$SOLR_TIP/$2"
              else
                SOLR_SERVER_DIR="$2"
              fi
            fi
            # resolve it to an absolute path
            SOLR_SERVER_DIR="$(cd "$SOLR_SERVER_DIR" || (echo "SOLR_SERVER_DIR not found" && exit 1); pwd)"
            shift 2
        ;;
        -s|-solr.home)
            if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
              print_usage "$SCRIPT_CMD" "Solr home directory is required when using the $1 option!"
              exit 1
            fi

            SOLR_HOME="$2"
            shift 2
        ;;
        -t|-data.home)
            SOLR_DATA_HOME="$2"
            shift 2
        ;;
        -e|-example)
            if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
              print_usage "$SCRIPT_CMD" "Example name is required when using the $1 option!"
              exit 1
            fi
            EXAMPLE="$2"
            shift 2
        ;;
        -f|-foreground)
            FG="true"
            shift
        ;;
        -h|-host)
            if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
              print_usage "$SCRIPT_CMD" "Hostname is required when using the $1 option!"
              exit 1
            fi
            SOLR_HOST="$2"
            PASS_TO_RUN_EXAMPLE+=("-h" "$SOLR_HOST")
            shift 2
        ;;
        -m|-memory)
            if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
              print_usage "$SCRIPT_CMD" "Memory setting is required when using the $1 option!"
              exit 1
            fi
            SOLR_HEAP="$2"
            PASS_TO_RUN_EXAMPLE+=("-m" "$SOLR_HEAP")
            shift 2
        ;;
        -p|-port)
            if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
              print_usage "$SCRIPT_CMD" "Port number is required when using the $1 option!"
              exit 1
            fi
            SOLR_PORT="$2"
            PROVIDED_SOLR_PORT="${SOLR_PORT}"
            PASS_TO_RUN_EXAMPLE+=("-p" "$SOLR_PORT")
            shift 2
        ;;
        -z|-zkhost|-zkHost)
            if [[ -z "$2" || "${2:0:1}" == "-" ]]; then
              print_usage "$SCRIPT_CMD" "Zookeeper connection string is required when using the $1 option!"
              exit 1
            fi
            ZK_HOST="$2"
            SOLR_MODE="solrcloud"
            PASS_TO_RUN_EXAMPLE+=("-z" "$ZK_HOST")
            shift 2
        ;;
        -a|-addlopts)
            ADDITIONAL_CMD_OPTS="$2"
            PASS_TO_RUN_EXAMPLE+=("-a" "$ADDITIONAL_CMD_OPTS")
            shift 2
        ;;
        -j|-jettyconfig)
            ADDITIONAL_JETTY_CONFIG="$2"
            PASS_TO_RUN_EXAMPLE+=("-j" "$ADDITIONAL_JETTY_CONFIG")
            shift 2
        ;;
        -k|-key)
            STOP_KEY="$2"
            shift 2
        ;;
        -help|-h)
            print_usage "$SCRIPT_CMD"
            exit 0
        ;;
        -noprompt)
            PASS_TO_RUN_EXAMPLE+=("-noprompt")
            shift
        ;;
        -V|-verbose)
            verbose=true
            PASS_TO_RUN_EXAMPLE+=("-verbose")
            shift
        ;;
        -v)
            SOLR_LOG_LEVEL=DEBUG
            shift
        ;;
        -q)
            SOLR_LOG_LEVEL=WARN
            shift
        ;;
        -all)
            stop_all=true
            shift
        ;;
        -force)
            FORCE=true
            PASS_TO_RUN_EXAMPLE+=("-force")
            shift
        ;;
        --)
            shift
            break
        ;;
        *)
            if [ -z "${1:-}" ]; then
              break # out-of-args, stop looping
            elif [ "${1:0:2}" == "-D" ]; then
              # pass thru any opts that begin with -D (java system props)
              # These should go to the end of SOLR_OPTS, as they should override everything else
              SOLR_OPTS+=("$1")
              PASS_TO_RUN_EXAMPLE+=("$1")
              shift
            else
              print_usage "$SCRIPT_CMD" "$1 is not supported by this script"
              exit 1
            fi
        ;;
    esac
  done
fi

# Default placement plugin
if [[ -n "${SOLR_PLACEMENTPLUGIN_DEFAULT:-}" ]] ; then
  SCRIPT_SOLR_OPTS+=("-Dsolr.placementplugin.default=$SOLR_PLACEMENTPLUGIN_DEFAULT")
fi

# Remote streaming and stream body
if [ "${SOLR_ENABLE_REMOTE_STREAMING:-false}" == "true" ]; then
  SCRIPT_SOLR_OPTS+=("-Dsolr.enableRemoteStreaming=true")
fi
if [ "${SOLR_ENABLE_STREAM_BODY:-false}" == "true" ]; then
  SCRIPT_SOLR_OPTS+=("-Dsolr.enableStreamBody=true")
fi

: ${SOLR_SERVER_DIR:=$DEFAULT_SERVER_DIR}

if [ ! -e "$SOLR_SERVER_DIR" ]; then
  echo -e "\nSolr server directory $SOLR_SERVER_DIR not found!\n"
  exit 1
fi

if [[ "$FG" == 'true' && -n "${EXAMPLE:-}" ]]; then
  FG='false'
  echo -e "\nWARNING: Foreground mode (-f) not supported when running examples.\n"
fi

#
# If the user specified an example to run, invoke the run_example tool (Java app) and exit
# otherwise let this script proceed to process the user request
#
if [ -n "${EXAMPLE:-}" ] && [ "$SCRIPT_CMD" == "start" ]; then
  run_tool run_example -e "$EXAMPLE" -d "$SOLR_SERVER_DIR" -urlScheme "$SOLR_URL_SCHEME" "${PASS_TO_RUN_EXAMPLE[@]}"
  exit $?
fi

############# start/stop logic below here ################

if $verbose ; then
  echo "Using Solr root directory: $SOLR_TIP"
  echo "Using Java: $JAVA"
  "$JAVA" -version
fi

if [ -n "${SOLR_HOST:-}" ]; then
  SOLR_HOST_ARG=("-Dhost=$SOLR_HOST")
elif [[ "${SOLR_JETTY_HOST:-127.0.0.1}" == "127.0.0.1" ]]; then
  # Jetty will only bind on localhost interface, so nodes must advertise themselves with localhost
  SOLR_HOST_ARG=("-Dhost=localhost")
else
  SOLR_HOST_ARG=()
fi

: "${STOP_KEY:=solrrocks}"

# stop all if no port specified or "all" is used
if [[ "$SCRIPT_CMD" == "stop" ]]; then
  if $stop_all; then
    none_stopped=true
    find "$SOLR_PID_DIR" -name "solr-*.pid" -type f | while read PIDF
      do
        NEXT_PID=$(cat "$PIDF")
        port=$(jetty_port "$NEXT_PID")
        if [ "$port" != "" ]; then
          stop_solr "$SOLR_SERVER_DIR" "$port" "$STOP_KEY" "$NEXT_PID"
          none_stopped=false
        fi
        rm -f "$PIDF"
    done
    # TODO: none_stopped doesn't get reflected across the subshell
    # This can be uncommented once we find a clean way out of it
    # if $none_stopped; then
    #   echo -e "\nNo Solr nodes found to stop.\n"
    # fi
    exit
  elif [[ -z "${PROVIDED_SOLR_PORT:-}" ]]; then
    # not stopping all and don't have a port, but if we can find a single pid file for Solr, then use that
    none_stopped=true
    numSolrs=$(find "$SOLR_PID_DIR" -name "solr-*.pid" -type f | wc -l | tr -d ' ')
    if [ "$numSolrs" -eq 1 ]; then
      # only do this if there is only 1 node running, otherwise they must provide the -p or -all
      PID="$(cat "$(find "$SOLR_PID_DIR" -name "solr-*.pid" -type f)")"
      CHECK_PID=$(ps -o pid='' -p "$PID" | tr -d ' ')
      if [ "$CHECK_PID" != "" ]; then
        port=$(jetty_port "$CHECK_PID")
        if [ "$port" != "" ]; then
          stop_solr "$SOLR_SERVER_DIR" "$port" "$STOP_KEY" "$CHECK_PID"
          none_stopped=false
        fi
      fi
    fi

    if $none_stopped; then
      if [ "$numSolrs" -gt 0 ]; then
        echo -e "\nFound $numSolrs Solr nodes running! Must either specify a port using -p or -all to stop all Solr nodes on this host.\n"
      else
        echo -e "\nNo Solr nodes found to stop.\n"
      fi
      exit 1
    fi
    exit
  fi
fi

if [ -n "${SOLR_PORT_ADVERTISE:-}" ]; then
  SCRIPT_SOLR_OPTS+=("-Dsolr.port.advertise=$SOLR_PORT_ADVERTISE")
fi

if [ -n "${SOLR_JETTY_HOST:-}" ]; then
  SCRIPT_SOLR_OPTS+=("-Dsolr.jetty.host=$SOLR_JETTY_HOST")
fi

if [ -n "${SOLR_ZK_EMBEDDED_HOST:-}" ]; then
  SCRIPT_SOLR_OPTS+=("-Dsolr.zk.embedded.host=$SOLR_ZK_EMBEDDED_HOST")
fi

: "${STOP_PORT:=$((SOLR_PORT - 1000))}"

if [ "$SCRIPT_CMD" == "start" ] || [ "$SCRIPT_CMD" == "restart" ] ; then
  if [[ $EUID -eq 0 ]] && [[ "$FORCE" == "false" ]] ; then
    echo "WARNING: Starting Solr as the root user is a security risk and not considered best practice. Exiting."
    echo "         Please consult the Reference Guide. To override this check, start with argument '-force'"
    exit 1
  fi
fi

if [[ "$SCRIPT_CMD" == "start" ]]; then
  # see if Solr is already running
  SOLR_PID=$(solr_pid_by_port "$SOLR_PORT")

  if [ -z "${SOLR_PID:-}" ]; then
    # not found using the pid file ... but use ps to ensure not found
    SOLR_PID=$(ps auxww | grep start\.jar | awk "/\-Djetty\.port=$SOLR_PORT/"' {print $2}' | sort -r)
  fi

  if [ -n "${SOLR_PID:-}" ]; then
    echo -e "\nPort $SOLR_PORT is already being used by another process (pid: $SOLR_PID)\nPlease choose a different port using the -p option.\n"
    exit 1
  fi
else
  # either stop or restart
  # see if Solr is already running
  SOLR_PID=$(solr_pid_by_port "$SOLR_PORT")
  if [ -z "$SOLR_PID" ]; then
    # not found using the pid file ... but use ps to ensure not found
    SOLR_PID=$(ps auxww | grep start\.jar | awk "/\-Djetty\.port=$SOLR_PORT/"' {print $2}' | sort -r)
  fi
  if [ "$SOLR_PID" != "" ]; then
    stop_solr "$SOLR_SERVER_DIR" "$SOLR_PORT" "$STOP_KEY" "$SOLR_PID"
  else
    if [ "$SCRIPT_CMD" == "stop" ]; then
      echo -e "No process found for Solr node running on port $SOLR_PORT"
      exit 1
    fi
  fi
fi

if [ -z "${SOLR_HOME:-}" ]; then
  SOLR_HOME="$SOLR_SERVER_DIR/solr"
elif [[ $SOLR_HOME != /* ]]; then
  if [[ -d "$(pwd -P)/$SOLR_HOME" ]]; then
    SOLR_HOME="$(pwd -P)/$SOLR_HOME"
  elif [[ -d "$SOLR_SERVER_DIR/$SOLR_HOME" ]]; then
    SOLR_HOME="$SOLR_SERVER_DIR/$SOLR_HOME"
    SOLR_PID_DIR="$SOLR_HOME"
  fi
fi

# Set the default configset dir to be bootstrapped as _default
: "${DEFAULT_CONFDIR:="$SOLR_SERVER_DIR/solr/configsets/_default/conf"}"

# This is quite hacky, but examples rely on a different log4j2.xml
# so that we can write logs for examples to $SOLR_HOME/../logs
: "${SOLR_LOGS_DIR:="$SOLR_SERVER_DIR/logs"}"
EXAMPLE_DIR="$SOLR_TIP/example"
# if SOLR_HOME is inside of EXAMPLE_DIR
if [ "${SOLR_HOME:0:${#EXAMPLE_DIR}}" = "$EXAMPLE_DIR" ]; then
  LOG4J_PROPS="$DEFAULT_SERVER_DIR/resources/log4j2.xml"
  SOLR_LOGS_DIR="$SOLR_HOME/../logs"
fi

# Set the logging manager by default, so that Lucene JUL logs are included with Solr logs.
LOG4J_CONFIG=("-Djava.util.logging.manager=org.apache.logging.log4j.jul.LogManager")
if [ -n "${LOG4J_PROPS:-}" ]; then
  LOG4J_CONFIG+=("-Dlog4j.configurationFile=$LOG4J_PROPS")
fi

if [ "$SCRIPT_CMD" == "stop" ]; then
  # already stopped, script is done.
  exit 0
fi

# NOTE: If the script gets to here, then it is starting up a Solr node.

if [ ! -e "$SOLR_HOME" ]; then
  echo -e "\nSolr home directory $SOLR_HOME not found!\n"
  exit 1
fi
if [[ -n ${SOLR_DATA_HOME:-} ]] && [ ! -e "$SOLR_DATA_HOME" ]; then
  echo -e "\nSolr data home directory $SOLR_DATA_HOME not found!\n"
  exit 1
fi

# Establish default GC logging opts if no env var set (otherwise init to sensible default)
if [ -z "${GC_LOG_OPTS}" ]; then
  if [[ "$JAVA_VER_NUM" -lt "9" ]] ; then
    GC_LOG_OPTS=('-verbose:gc' '-XX:+PrintHeapAtGC' '-XX:+PrintGCDetails' \
                 '-XX:+PrintGCDateStamps' '-XX:+PrintGCTimeStamps' '-XX:+PrintTenuringDistribution' \
                 '-XX:+PrintGCApplicationStoppedTime')
  else
    GC_LOG_OPTS=('-Xlog:gc*')
  fi
else
  # TODO: Should probably not overload GC_LOG_OPTS as both string and array, but leaving it be for now
  # shellcheck disable=SC2128
  GC_LOG_OPTS=($GC_LOG_OPTS)
fi

# if verbose gc logging enabled, setup the location of the log file and rotation
if [ "${#GC_LOG_OPTS[@]}" -gt 0 ]; then
  if [[ "$JAVA_VER_NUM" -lt "9" ]] || [ "$JAVA_VENDOR" == "OpenJ9" ]; then
    gc_log_flag="-Xloggc"
    if [ "$JAVA_VENDOR" == "OpenJ9" ]; then
      gc_log_flag="-Xverbosegclog"
    fi
    if [ -z ${JAVA8_GC_LOG_FILE_OPTS+x} ]; then
      GC_LOG_OPTS+=("$gc_log_flag:$SOLR_LOGS_DIR/solr_gc.log" '-XX:+UseGCLogFileRotation' '-XX:NumberOfGCLogFiles=9' '-XX:GCLogFileSize=20M')
    else
      GC_LOG_OPTS+=($JAVA8_GC_LOG_FILE_OPTS)
    fi
  else
    # https://openjdk.java.net/jeps/158
    for i in "${!GC_LOG_OPTS[@]}";
    do
      # for simplicity, we only look at the prefix '-Xlog:gc'
      # (if 'all' or multiple tags are used starting with anything other then 'gc' the user is on their own)
      # if a single additional ':' exists in param, then there is already an explicit output specifier
      # shellcheck disable=SC2001
      GC_LOG_OPTS[$i]=$(echo "${GC_LOG_OPTS[$i]}" | sed "s|^\(-Xlog:gc[^:]*$\)|\1:file=$SOLR_LOGS_DIR/solr_gc.log:time,uptime:filecount=9,filesize=20M|")
    done
  fi
fi

# If ZK_HOST is defined, the assume SolrCloud mode
if [[ -n "${ZK_HOST:-}" ]]; then
  SOLR_MODE="solrcloud"
fi

if [ "${SOLR_MODE:-}" == 'solrcloud' ]; then
  : "${ZK_CLIENT_TIMEOUT:=30000}"
  CLOUD_MODE_OPTS=("-DzkClientTimeout=$ZK_CLIENT_TIMEOUT")

  if [ -n "${ZK_HOST:-}" ]; then
    CLOUD_MODE_OPTS+=("-DzkHost=$ZK_HOST")
  else
    if [ $SOLR_PORT -gt 64535 ]; then
      echo -e "\nZK_HOST is not set and Solr port is $SOLR_PORT, which would result in an invalid embedded Zookeeper port!\n"
      exit 1
    fi
    if $verbose ; then
      echo "Configuring SolrCloud to launch an embedded Zookeeper using -DzkRun"
    fi

    CLOUD_MODE_OPTS+=('-DzkRun')
  fi

  if [ -n "${ZK_CREATE_CHROOT:-}" ]; then
    CLOUD_MODE_OPTS+=("-DcreateZkChroot=$ZK_CREATE_CHROOT")
  fi

  # and if collection1 needs to be bootstrapped
  if [ -e "$SOLR_HOME/collection1/core.properties" ]; then
    CLOUD_MODE_OPTS+=('-Dbootstrap_confdir=./solr/collection1/conf' '-Dcollection.configName=myconf' '-DnumShards=1')
  fi

  if [ "${SOLR_SOLRXML_REQUIRED:-false}" == "true" ]; then
    CLOUD_MODE_OPTS+=("-Dsolr.solrxml.required=true")
  fi
else
  if [ ! -e "$SOLR_HOME/solr.xml" ] && [ "${SOLR_SOLRXML_REQUIRED:-}" == "true" ]; then
    echo -e "\nSolr home directory $SOLR_HOME must contain a solr.xml file!\n"
    exit 1
  fi
fi

# Exit if old syntax found
if [ -n "${SOLR_IP_BLACKLIST:-}" ] || [ -n "${SOLR_IP_WHITELIST:-}" ]; then
  echo "ERROR: SOLR_IP_BLACKLIST and SOLR_IP_WHITELIST are no longer supported. Please use SOLR_IP_ALLOWLIST and SOLR_IP_DENYLIST instead."
  exit 1
fi

# IP-based access control
IP_ACL_OPTS=("-Dsolr.jetty.inetaccess.includes=${SOLR_IP_ALLOWLIST:-}" \
             "-Dsolr.jetty.inetaccess.excludes=${SOLR_IP_DENYLIST:-}")

# These are useful for attaching remote profilers like VisualVM/JConsole
if [ "${ENABLE_REMOTE_JMX_OPTS:-false}" == "true" ]; then

  if [ -z "$RMI_PORT" ]; then
    RMI_PORT=$((SOLR_PORT + 10000))
    if [ $RMI_PORT -gt 65535 ]; then
      echo -e "\nRMI_PORT is $RMI_PORT, which is invalid!\n"
      exit 1
    fi
  fi

  REMOTE_JMX_OPTS=('-Dcom.sun.management.jmxremote' \
    '-Dcom.sun.management.jmxremote.local.only=false' \
    '-Dcom.sun.management.jmxremote.ssl=false' \
    '-Dcom.sun.management.jmxremote.authenticate=false' \
    "-Dcom.sun.management.jmxremote.port=$RMI_PORT" \
    "-Dcom.sun.management.jmxremote.rmi.port=$RMI_PORT")

  # if the host is set, then set that as the rmi server hostname
  if [ "$SOLR_HOST" != "" ]; then
    REMOTE_JMX_OPTS+=("-Djava.rmi.server.hostname=$SOLR_HOST")
  fi
else
  REMOTE_JMX_OPTS=()
fi

# Enable java security manager (allowing filesystem access and other things)
if [ "${SOLR_SECURITY_MANAGER_ENABLED:-true}" == "true" ]; then
  SECURITY_MANAGER_OPTS=('-Djava.security.manager' \
      "-Djava.security.policy=${SOLR_SERVER_DIR}/etc/security.policy" \
      "-Djava.security.properties=${SOLR_SERVER_DIR}/etc/security.properties" \
      '-Dsolr.internal.network.permission=*')
else
  SECURITY_MANAGER_OPTS=()
fi

# Enable ADMIN UI by default, and give the option for users to disable it
if [ "${SOLR_ADMIN_UI_DISABLED:-false}" == "true" ]; then
  SOLR_ADMIN_UI="-DdisableAdminUI=true"
  echo -e "ADMIN UI Disabled"
else
  SOLR_ADMIN_UI="-DdisableAdminUI=false"
fi

JAVA_MEM_OPTS=()
if [ -z "${SOLR_HEAP:-}" ] && [ -n "${SOLR_JAVA_MEM:-}" ]; then
  JAVA_MEM_OPTS=($SOLR_JAVA_MEM)
else
  SOLR_HEAP="${SOLR_HEAP:-512m}"
  JAVA_MEM_OPTS=("-Xms$SOLR_HEAP" "-Xmx$SOLR_HEAP")
fi

# Pick default for Java thread stack size, and then add to SCRIPT_SOLR_OPTS
SCRIPT_SOLR_OPTS+=(${SOLR_JAVA_STACK_SIZE:-"-Xss256k"})

: "${SOLR_TIMEZONE:=UTC}"

function mk_writable_dir() {
  local DIRNAME="$1"
  local DESCRIPTION="$2"
  if ! mkdir -p "$DIRNAME" 2> /dev/null ; then
    echo -e "\nERROR: $DESCRIPTION directory $DIRNAME could not be created. Exiting"
    exit 1
  fi
  if [ ! -w "$DIRNAME" ]; then
    echo -e "\nERROR: $DESCRIPTION directory $DIRNAME is not writable. Exiting"
    exit 1
  fi
}

# Launches Solr in foreground/background depending on parameters
function start_solr() {

  run_in_foreground="$1"
  stop_port="$STOP_PORT"

  SOLR_ADDL_ARGS="$2"
  SOLR_JETTY_ADDL_CONFIG="$3"

  # define default GC_TUNE
  if [ -z "${GC_TUNE}" ]; then
      GC_TUNE_ARR=('-XX:+UseG1GC' \
        '-XX:+PerfDisableSharedMem' \
        '-XX:+ParallelRefProcEnabled' \
        '-XX:MaxGCPauseMillis=250' \
        '-XX:+UseLargePages' \
        '-XX:+AlwaysPreTouch' \
        '-XX:+ExplicitGCInvokesConcurrent')
  else
    # shellcheck disable=SC2128
    GC_TUNE_ARR=($GC_TUNE) # Stuff the string from outside into first value of the array
  fi

  if [ -n "${SOLR_WAIT_FOR_ZK:-}" ]; then
    SCRIPT_SOLR_OPTS+=("-DwaitForZk=$SOLR_WAIT_FOR_ZK")
  fi

  if [ -n "${SOLR_DATA_HOME:-}" ]; then
    SCRIPT_SOLR_OPTS+=("-Dsolr.data.home=$SOLR_DATA_HOME")
  fi

  if [ -n "${SOLR_DELETE_UNKNOWN_CORES:-}" ]; then
    SCRIPT_SOLR_OPTS+=("-Dsolr.deleteUnknownCores=$SOLR_DELETE_UNKNOWN_CORES")
  fi

  # If SSL-related system props are set, add them to SCRIPT_SOLR_OPTS
  if [ "$SOLR_SSL_ENABLED" == "true" ]; then
    # If using SSL and solr.jetty.https.port not set explicitly, use the jetty.port
    SSL_PORT_PROP="-Dsolr.jetty.https.port=$SOLR_PORT"
    SCRIPT_SOLR_OPTS+=($SOLR_SSL_OPTS "$SSL_PORT_PROP")
  fi

  # If authentication system props are set, add them to SCRIPT_SOLR_OPTS
  if [ -n "$AUTHC_OPTS" ]; then
    SCRIPT_SOLR_OPTS+=($AUTHC_OPTS)
  fi

  # If there are internal options set by Solr (users should not use this variable), add them to SCRIPT_SOLR_OPTS
  if [ -n "$SOLR_OPTS_INTERNAL" ]; then
    SCRIPT_SOLR_OPTS+=($SOLR_OPTS_INTERNAL)
  fi

  # If a heap dump directory is specified, enable it in SCRIPT_SOLR_OPTS
  if [[ -z "${SOLR_HEAP_DUMP_DIR:-}" ]] && [[ "${SOLR_HEAP_DUMP:-}" == "true" ]]; then
    SOLR_HEAP_DUMP_DIR="${SOLR_LOGS_DIR}/dumps"
  fi
  if [[ -n "${SOLR_HEAP_DUMP_DIR:-}" ]]; then
    SCRIPT_SOLR_OPTS+=("-XX:+HeapDumpOnOutOfMemoryError")
    SCRIPT_SOLR_OPTS+=("-XX:HeapDumpPath=$SOLR_HEAP_DUMP_DIR/solr-$(date +%s)-pid$$.hprof")
  fi

  if $verbose ; then
    echo -e "\nStarting Solr using the following settings:"
    echo -e "    JAVA               = $JAVA"
    echo -e "    SOLR_SERVER_DIR    = $SOLR_SERVER_DIR"
    echo -e "    SOLR_HOME          = $SOLR_HOME"
    echo -e "    SOLR_HOST          = ${SOLR_HOST:-}"
    echo -e "    SOLR_PORT          = $SOLR_PORT"
    echo -e "    STOP_PORT          = $STOP_PORT"
    echo -e "    JAVA_MEM_OPTS      = ${JAVA_MEM_OPTS[*]}"
    echo -e "    GC_TUNE            = ${GC_TUNE_ARR[*]}"
    echo -e "    GC_LOG_OPTS        = ${GC_LOG_OPTS[*]}"
    echo -e "    SOLR_TIMEZONE      = $SOLR_TIMEZONE"

    if [ "$SOLR_MODE" == "solrcloud" ]; then
      echo -e "    CLOUD_MODE_OPTS    = ${CLOUD_MODE_OPTS[*]}"
    fi

    if [ -n "${SOLR_OPTS:-}" ]; then
      echo -e "    SOLR_OPTS (USER)   = ${SOLR_OPTS[*]}"
    fi

    if [ -n "${SCRIPT_SOLR_OPTS:-}" ]; then
      echo -e "    SOLR_OPTS (SCRIPT) = ${SCRIPT_SOLR_OPTS[*]}"
    fi

    if [ -n "${SOLR_ADDL_ARGS:-}" ]; then
      echo -e "    SOLR_ADDL_ARGS     = $SOLR_ADDL_ARGS"
    fi

    if [ "${ENABLE_REMOTE_JMX_OPTS:-false}" == "true" ]; then
      echo -e "    RMI_PORT           = ${RMI_PORT:-}"
      echo -e "    REMOTE_JMX_OPTS    = ${REMOTE_JMX_OPTS[*]}"
    fi

    if [ -n "${SOLR_LOG_LEVEL:-}" ]; then
      echo -e "    SOLR_LOG_LEVEL     = $SOLR_LOG_LEVEL"
    fi

    if [ -n "${SOLR_DATA_HOME:-}" ]; then
      echo -e "    SOLR_DATA_HOME     = $SOLR_DATA_HOME"
    fi
    echo
  fi

  # need to launch solr from the server dir
  cd "$SOLR_SERVER_DIR" || (echo -e "\nCd to SOLR_SERVER_DIR failed" && exit 1)

  if [ ! -e "$SOLR_SERVER_DIR/start.jar" ]; then
    echo -e "\nERROR: start.jar file not found in $SOLR_SERVER_DIR!\nPlease check your -d parameter to set the correct Solr server directory.\n"
    exit 1
  fi

  # Workaround for JIT crash, see https://issues.apache.org/jira/browse/SOLR-16463
  if [[ "$JAVA_VER_NUM" -ge "17" ]] ; then
    SCRIPT_SOLR_OPTS+=("-XX:CompileCommand=exclude,com.github.benmanes.caffeine.cache.BoundedLocalCache::put")
    echo "Java $JAVA_VER_NUM detected. Enabled workaround for SOLR-16463"
  fi

  # Vector optimizations are only supported for Java 20 and 21 for now.
  # This will need to change as Lucene is upgraded and newer Java versions are released
  if [[ "$JAVA_VER_NUM" -ge "20" ]] && [[ "$JAVA_VER_NUM" -le "21" ]] ; then
    SCRIPT_SOLR_OPTS+=("--add-modules" "jdk.incubator.vector")
    echo "Java $JAVA_VER_NUM detected. Incubating Panama Vector APIs have been enabled"
  fi

  SOLR_START_OPTS=('-server' "${JAVA_MEM_OPTS[@]}" "${GC_TUNE_ARR[@]}" "${GC_LOG_OPTS[@]}" "${IP_ACL_OPTS[@]}" \
    "${REMOTE_JMX_OPTS[@]}" "${CLOUD_MODE_OPTS[@]}" -Dsolr.log.dir="$SOLR_LOGS_DIR" \
    "-Djetty.port=$SOLR_PORT" "-DSTOP.PORT=$stop_port" "-DSTOP.KEY=$STOP_KEY" \
    # '-OmitStackTraceInFastThrow' ensures stack traces in errors,
    # users who don't care about useful error msgs can override in SOLR_OPTS with +OmitStackTraceInFastThrow
    "${SOLR_HOST_ARG[@]}" "-Duser.timezone=$SOLR_TIMEZONE" "-XX:-OmitStackTraceInFastThrow" \
    # '+CrashOnOutOfMemoryError' ensures that Solr crashes whenever
    # OOME is thrown. Program operation after OOME is unpredictable.
    "-XX:+CrashOnOutOfMemoryError" "-XX:ErrorFile=${SOLR_LOGS_DIR}/jvm_crash_%p.log" \
    "-Djetty.home=$SOLR_SERVER_DIR" "-Dsolr.solr.home=$SOLR_HOME" "-Dsolr.install.dir=$SOLR_TIP" "-Dsolr.install.symDir=$SOLR_TIP_SYM" \
    "-Dsolr.default.confdir=$DEFAULT_CONFDIR" "${LOG4J_CONFIG[@]}" "${SCRIPT_SOLR_OPTS[@]}" "${SECURITY_MANAGER_OPTS[@]}" "${SOLR_ADMIN_UI}" "${SOLR_OPTS[@]}")

  mk_writable_dir "$SOLR_LOGS_DIR" "Logs"
  if [[ -n "${SOLR_HEAP_DUMP_DIR:-}" ]]; then
    mk_writable_dir "$SOLR_HEAP_DUMP_DIR" "Heap Dump"
  fi
  case "$SOLR_LOGS_DIR" in
    contexts|etc|lib|modules|resources|scripts|solr|solr-webapp)
      echo -e "\nERROR: Logs directory $SOLR_LOGS_DIR is invalid. Reserved for the system. Exiting"
      exit 1
      ;;
  esac

  if [ "$run_in_foreground" == "true" ]; then
    # shellcheck disable=SC2086
    exec "$JAVA" "${SOLR_START_OPTS[@]}" $SOLR_ADDL_ARGS -jar start.jar "${SOLR_JETTY_CONFIG[@]}" $SOLR_JETTY_ADDL_CONFIG
  else
    # run Solr in the background
    # shellcheck disable=SC2086
    nohup "$JAVA" "${SOLR_START_OPTS[@]}" $SOLR_ADDL_ARGS -Dsolr.log.muteconsole \
        -jar start.jar "${SOLR_JETTY_CONFIG[@]}" $SOLR_JETTY_ADDL_CONFIG \
        1>"$SOLR_LOGS_DIR/solr-$SOLR_PORT-console.log" 2>&1 & echo $! > "$SOLR_PID_DIR/solr-$SOLR_PORT.pid"

    # Check and warn about low entropy on Linux systems
    if [ -e /proc/sys/kernel/random ]; then
      # Get the current entropy available
      entropy_avail=$(cat /proc/sys/kernel/random/entropy_avail)

      # Get the pool size
      pool_size=$(cat /proc/sys/kernel/random/poolsize)

      # Check if entropy is available and pool size is non-zero
      if [[ $entropy_avail -gt 0 && $pool_size -ne 0 ]]; then
        # Compute the ratio of entropy available to pool size
        ratio=$(awk -v ea="$entropy_avail" -v ps="$pool_size" 'BEGIN {print int((ea/ps)*100)}')

        # Check if the ratio is less than 25%
        if (( ratio < 25 )); then
          echo "Warning: Available entropy is low. As a result, use of the UUIDField, SSL, or any other features that require"
          echo "RNG might not work properly. To check for the amount of available entropy, use 'cat /proc/sys/kernel/random/entropy_avail'."
        fi
      else
        echo "Error: Either no entropy is available or the pool size is zero."
      fi
    fi

    # no lsof on cygwin though
    if lsof -v 2>&1 | grep -q revision; then
      echo -n "Waiting up to $SOLR_START_WAIT seconds to see Solr running on port $SOLR_PORT"
      # Launch in a subshell to show the spinner
      (loops=0
      while true
      do
        running=$(lsof -t -PniTCP:$SOLR_PORT -sTCP:LISTEN || :)
        if [ -z "${running:-}" ]; then
          slept=$((loops * 2))
          if [ $slept -lt $SOLR_START_WAIT ]; then
            sleep 2
            loops=$((loops+1))
          else
            echo -e "Still not seeing Solr listening on $SOLR_PORT after $SOLR_START_WAIT seconds!"
            tail -30 "$SOLR_LOGS_DIR/solr.log"
            exit # subshell!
          fi
        else
          SOLR_PID=$(ps auxww | grep start\.jar | awk "/\-Djetty\.port=$SOLR_PORT/"' {print $2}' | sort -r)
          echo -e "\nStarted Solr server on port $SOLR_PORT (pid=$SOLR_PID). Happy searching!\n"
          exit # subshell!
        fi
      done) &
      spinner $!
    else
      echo -e "NOTE: Please install lsof as this script needs it to determine if Solr is listening on port $SOLR_PORT."
      sleep 10
      SOLR_PID=$(ps auxww | grep start\.jar | awk "/\-Djetty\.port=$SOLR_PORT/"' {print $2}' | sort -r)
      echo -e "\nStarted Solr server on port $SOLR_PORT (pid=$SOLR_PID). Happy searching!\n"
      return;
    fi
  fi
}

start_solr "$FG" "${ADDITIONAL_CMD_OPTS:-}" "${ADDITIONAL_JETTY_CONFIG:-}"

exit $?
