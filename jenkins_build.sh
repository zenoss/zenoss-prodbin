#!/bin/bash

# Required Parameters
#
# The following parameters are set by Jenkins if you initiate the job
# in the Jenkins project. If you wish to run this script in the
# command line, feed the following parameters to the script.
#
# WORKSPACE: the absolute path of the directory assigned to the build
#            as a workspace.
# JOB_BASE_NAME: the last segment of $WORKSPACE, such as "foo" for
#                "/bar/foo".

set -ex

check_var() {
    if [ -z "$1" ]; then
        echo ERROR: undefined variable
        exit 1
    fi
}

# Check if all required parameters are defined.
echo Checking WORKSPACE;check_var $WORKSPACE;echo OK
echo Checking JOB_BASE_NAME;check_var $JOB_BASE_NAME;echo OK

# The name of the repo this job will checkout
REPO_NAME=zenoss-prodbin
# The branch of the repo this job will use
if [ -z "${BRANCH}" ]; then BRANCH=develop; fi
#ZENDEV_REPO=git@github.com:zenoss/zendev.git
ZENDEV_REPO=https://github.com/zenoss/zendev.git
# The zendev branch this job will use
if [ -z "${ZENDEV_BRANCH}" ]; then ZENDEV_BRANCH=zendev2; fi
if [ -z "${ZENDEV_VER}" ]; then ZENDEV_VER=0.2.0; fi
if [ -z "${GO_VER}" ]; then GO_VER=1.7.4; fi
# The name of the zendev environment that will be created.
# This name will be used as the devimg tag as well.
ZENDEV_ENV=${REPO_NAME}-${JOB_BASE_NAME}
# The repo that is checked out will be copied to this path
# inside zendev.
REPO_PATH=$WORKSPACE/${ZENDEV_ENV}/src/github.com/zenoss/${REPO_NAME}

# Check if all other parameters are defined.
echo Checking REPO_NAME;check_var $REPO_NAME;echo OK
echo Checking BRANCH;check_var $BRANCH;echo OK
echo Checking ZENDEV_REPO;check_var $ZENDEV_REPO;echo OK
echo Checking ZENDEV_BRANCH;check_var $ZENDEV_BRANCH;echo OK
echo Checking ZENDEV_VER;check_var $ZENDEV_VER;echo OK
echo Checking GO_VER;check_var $GO_VER;echo OK

echo Creating a virtual env...
if [ ! -d venv ]; then virtualenv venv; fi
source venv/bin/activate
if [ ! -d zendev ]; then git clone ${ZENDEV_REPO} zendev; fi
cd zendev;git checkout ${ZENDEV_BRANCH}
pip install -e .
ZENDEV_VER_ACTUAL=`zendev version`
if [ "${ZENDEV_VER_ACTUAL}" != "${ZENDEV_VER}" ]; then
    echo "ERROR: expected zendev version ${ZENDEV_VER}, but found ${ZENDEV_VER_ACTUAL}"
    exit 1
fi
echo Use zendev version ${ZENDEV_VER}

source $GVM_ROOT/scripts/gvm
gvm use go${GO_VER}
echo Use go version ${GO_VER}

echo Installing jig...
GOPATH=$WORKSPACE/goworld go get github.com/iancmcc/jig
echo $(which jig)
#export PATH="$GOPATH/bin:$PATH"

echo Boostraping zendev...
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
