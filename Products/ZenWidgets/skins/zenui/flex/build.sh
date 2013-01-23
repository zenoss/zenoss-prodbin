#!/bin/sh
echo "Building ZenNetMap.swf"
mxmlc -library-path+="comfolderfoundinbranch/springGraph" --show-actionscript-warnings=true --strict=true -file-specs ZenNetMap.mxml
