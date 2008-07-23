#!/bin/sh
echo "Building ZenNetMap.swf"
mxmlc -library-path+="SpringGraph.swc" --show-actionscript-warnings=true --strict=true -file-specs ZenNetMap.mxml
