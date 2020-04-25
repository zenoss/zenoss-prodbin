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
# BUILD_ID: the id of the current build job. It will be used in the name of
#           zendev environment, which the build job will create.
# BRANCH: the branch of the repo that the build job will use.
# ASSEMBLY_BRANCH: the product-assembly branch used to initialize zendev

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
echo Checking BRANCH;check_var $BRANCH;echo OK

# The product-assembly branch this job will use
if [ -z "${ASSEMBLY_BRANCH}" ]; then ASSEMBLY_BRANCH=$BRANCH; fi

# The name of the repo this job will checkout
REPO_NAME=zenoss-prodbin
ZENDEV_REPO=git@github.com:zenoss/zendev.git
# The zendev branch this job will use
if [ -z "${ZENDEV_BRANCH}" ]; then ZENDEV_BRANCH=zendev2; fi
if [ -z "${ZENDEV_VER}" ]; then ZENDEV_VER=0.2.0; fi
if [ -z "${GO_VER}" ]; then GO_VER=1.7.4; fi
# The name of the zendev environment that will be created.
# This name will be used as the devimg tag as well.
ZENDEV_ENV=${REPO_NAME}-${JOB_BASE_NAME}-${BUILD_ID}
ZENDEV_ROOT=$WORKSPACE/${ZENDEV_ENV}
# The repo that is checked out will be copied to this path
# inside zendev.
REPO_PATH=${ZENDEV_ROOT}/src/github.com/zenoss/${REPO_NAME}

cleanup() {
    RC="$?"
    if [[ $RC == 0 ]]; then
        zendev drop ${ZENDEV_ENV}
        docker rmi zendev/devimg:${ZENDEV_ENV} zendev/devimg-base:${ZENDEV_ENV}
    fi
}

trap cleanup INT TERM EXIT

# Check if all other parameters are defined.
echo Checking REPO_NAME;check_var $REPO_NAME;echo OK
echo Checking BRANCH;check_var $BRANCH;echo OK
echo Checking ZENDEV_REPO;check_var $ZENDEV_REPO;echo OK
echo Checking ZENDEV_BRANCH;check_var $ZENDEV_BRANCH;echo OK
echo Checking ZENDEV_VER;check_var $ZENDEV_VER;echo OK
echo Checking GO_VER;check_var $GO_VER;echo OK
echo Checking ASSEMBLY_BRANCH;check_var $ASSEMBLY_BRANCH;echo OK

echo Creating a virtual env...
if [ ! -d venv ]; then virtualenv venv; fi
source venv/bin/activate
pip install --upgrade pip
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
GOPATH=$WORKSPACE/goworld
go get github.com/iancmcc/jig
export PATH=$GOPATH/bin:$PATH
JIG="$(which jig)"
echo Checking JIG; check_var $JIG; echo OK

echo Boostraping zendev...
source $(zendev bootstrap)

echo Creating a zendev environment...
cd $WORKSPACE
zendev init --shallow --tag $ASSEMBLY_BRANCH ${ZENDEV_ENV}
zendev use ${ZENDEV_ENV}
echo Use ${ZENDEV_ENV} zendev environment

# The Jenkins project is configured to checkout to a sub-directory
# named REPO_NAME. Copy this to the zendev environment created above.
rm -rf ${REPO_PATH}
cp -r $WORKSPACE/${REPO_NAME} ${REPO_PATH}

echo Creating a devimg...
zendev devimg --clean

# Copy contents of the bin directory as those scripts may differ between
# the base branch and the PR branch.  Exclude the metrics directory because
# that directory is symlinked back into the source repo.
echo Copying zenoss-prodbin/bin/ to zenhome/bin
rsync -av --exclude=metrics/ ${REPO_PATH}/bin/ ${ZENDEV_ROOT}/zenhome/bin

echo Running the tests...
pushd ${ZENDEV_ROOT}/src/github.com/zenoss/product-assembly
export PRODUCT_IMAGE_ID=zendev/devimg:${ZENDEV_ENV}
export MARIADB_IMAGE_ID=zendev/mariadb:${ZENDEV_ENV}
./test_image.sh \
	--no-zenpacks \
	--mount ${HOME}/.m2:/home/zenoss/.m2 \
	--mount ${ZENDEV_ROOT}/zenhome:/opt/zenoss \
	--mount ${ZENDEV_ROOT}/var_zenoss:/var/zenoss \
	--mount ${ZENDEV_ROOT}/src/github.com/zenoss:/mnt/src \
	--env SRCROOT=/mnt/src
popd

echo Building the artifacts...
cdz ${REPO_NAME};make clean build
