set -e

REPO_NAME=zenoss-prodbin
REPO_PATH=$WORKSPACE/${ZENDEV_ENV}/src/github.com/zenoss/${REPO_NAME}
BRANCH=develop
# The name of the zendev environment that will be created. This name will be used as the devimg tag as well.
ZENDEV_ENV=${REPO_NAME}-${JOB_BASE_NAME}
ZENDEV_REPO=git@github.com:zenoss/zendev.git
ZENDEV_DIR=zendev
ZENDEV_BRANCH=zendev2
ZENDEV_VER=0.2.0
VENV_DIR=venv
GO_VER=1.7.4

echo Creating a virtual env...
virtualenv ${VENV_DIR}
source ${VENV_DIR}/bin/activate
git clone ${ZENDEV_REPO} ${ZENDEV_DIR}
cd ${ZENDEV_DIR};git checkout ${ZENDEV_BRANCH}
pip install -e .
zendev version | grep ${ZENDEV_VER} # Check zendev version

echo Use go version ${GO_VER}
source $GVM_ROOT/scripts/gvm
gvm use go${GO_VER}
GOPATH=$WORKSPACE/goworld go get github.com/iancmcc/jig

source $(zendev bootstrap)

echo Creating a zendev environment...
cd $WORKSPACE
zendev init --tag $BRANCH ${ZENDEV_ENV}
zendev use ${ZENDEV_ENV}

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
