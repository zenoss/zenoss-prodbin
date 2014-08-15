#!/bin/sh
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

# ERROR CODES
MISSING_JDK_1_6=4
CANNOT_MAKE_TEMP_DIR=5
MISSING_WGET_AND_CURL=6
MISSING_UNZIP=7
UNZIP_ERROR=8
ERROR_MOVING_JARFILE=9


do_exit(){
    echo $1
    exit $2
}

JAVA_CHECK=`java -version 2>&1 | grep "java version \"1.[6-9]"`
if [ -z "$JAVA_CHECK" ]; then
    which java
    do_exit "This script requires the Sun JDK 1.6 or greater." $MISSING_JDK_1_6
fi

if [ -z "$JSBUILDER" ]; then
    JSBUILDER=$ZENHOME/share/java/sencha_jsbuilder-2/JSBuilder2.jar
    echo "\$JSBUILDER not set. Defaulting to $JSBUILDER."
fi

if [ ! -f "$JSBUILDER" ]; then
    echo "Unable to find JSBuilder jar at location $JSNUILDER, exiting"
    exit 1
fi

JSHOME=$DESTDIR$ZENHOME/Products/ZenUI3/browser
java -jar $JSBUILDER -p $JSHOME/zenoss.jsb2 -d $JSHOME -v
exit $?
