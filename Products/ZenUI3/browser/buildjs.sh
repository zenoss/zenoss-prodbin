#!/bin/sh

if [ -z "$JSBUILDER" ]; then
    JSBUILDER=$ZENHOME/JSBuilder2.jar
    echo "\$JSBUILDER not set. Defaulting to $JSBUILDER."
fi
JSHOME="$ZENHOME/Products/ZenUI3/browser"
java -jar $JSBUILDER -p $JSHOME/zenoss.jsb2 -d $JSHOME -v
