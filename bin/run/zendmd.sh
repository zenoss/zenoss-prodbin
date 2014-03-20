#! /usr/bin/env bash                                                                                                                       
############################################################################## 
#                                                                              
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.                        
#                                                                              
# This content is made available according to terms specified in               
# License.zenoss under the directory where your Zenoss product is installed.   
#                                                                              
##############################################################################   

__DEFAULT__() {
    ${ZENHOME:-/opt/zenoss}/bin/zendmd $@
    exit 0
}
