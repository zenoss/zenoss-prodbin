#! /usr/bin/env bash                                                                                                                       
############################################################################## 
#                                                                              
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.                        
#                                                                              
# This content is made available according to terms specified in               
# License.zenoss under the directory where your Zenoss product is installed.   
#                                                                              
##############################################################################   


echo -e
echo -e
echo -e "    This is an example template for a 'serviced run ...' command.  "
echo -e "    Each custom script must include a function '__DEFAULT__', which "
echo -e "    defines the default action to be performed by the host when the "
echo -e "    command completes and functions for each custom command that "
echo -e "    requires a specific action from the host."
echo -e
echo -e "    Defined Commands:"
echo -e "        testcommit    testdiscard"
echo -e
echo -e

__DEFAULT__() {
    if [[ $1 != "" ]]; then
        echo -e "command not defined: $1"
        exit 255
    fi
    exit 1
}

testcommit() {
    echo -e "signaling host to commit the container ..."
    exit 0
}

testdiscard() {
    echo -e "signaling host to discard the container ..."
    exit 1
}