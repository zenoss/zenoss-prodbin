#!/bin/bash
set -ex

# Required parameters
# REPO_NAME: the name of the repo this job will checkout
# BRANCH: the branch of the repo this job will use
# ZENDEV_REPO: the zendev repo
# ZENDEV_BRANCH: the zendev branch this job will use
# ZENDEV_VER: the zendev version
# GO_VER: the go version

check_var() {
    if [ -z "$1" ]; then
        echo Undefined variable
        exit 1
    fi
}

REPO_NAME=zenoss-prodbin
BRANCH=develop
ZENDEV_REPO=git@github.com:zenoss/zendev.git
ZENDEV_BRANCH=zendev2
ZENDEV_VER=0.2.0
GO_VER=1.7.4

# The name of the zendev environment that will be created.
# This name will be used as the devimg tag as well.
ZENDEV_ENV=${REPO_NAME}-${JOB_BASE_NAME}

# The repo that is checked out will be copied to this path
# inside zendev.
REPO_PATH=$WORKSPACE/${ZENDEV_ENV}/src/github.com/zenoss/${REPO_NAME}

# Check if all required parameters are defined.
echo REPO_NAME;check_var $REPO_NAME;echo OK
echo BRANCH;check_var $BRANCH;echo OK
echo ZENDEV_REPO;check_var $ZENDEV_REPO;echo OK
echo ZENDEV_BRANCH;check_var $ZENDEV_BRANCH;echo OK
echo ZENDEV_VER;check_var $ZENDEV_VER;echo OK
echo GO_VER;check_var $GO_VER;echo OK

echo Creating a virtual env...
virtualenv venv
source venv/bin/activate
git clone ${ZENDEV_REPO} zendev
cd zendev;git checkout ${ZENDEV_BRANCH}
pip install -e .
zendev version | grep ${ZENDEV_VER} # Check zendev version
echo Use zendev version ${ZENDEV_VER}

source $GVM_ROOT/scripts/gvm
gvm use go${GO_VER}
echo Use go version ${GO_VER}

GOPATH=$WORKSPACE/goworld go get github.com/iancmcc/jig
source $(zendev bootstrap)

echo Creating a zendev environment...
cd $WORKSPACE
zendev init --tag $BRANCH ${ZENDEV_ENV}
zendev use ${ZENDEV_ENV}
echo Use ${ZENDEV_ENV} zendev environment

# The Jenkins project is configured to checkout to a sub-directory
# named REPO_NAME. Copy this to the zendev environment created above.
rm -rf ${REPO_PATH}
cp -r $WORKSPACE/${REPO_NAME} ${REPO_PATH}

echo Creating a devimg...
zendev devimg --clean

echo Running the tests...
zendev test --no-tty -- --no-zenpacks

echo Building the artifacts...
cdz ${REPO_NAME};make clean build
