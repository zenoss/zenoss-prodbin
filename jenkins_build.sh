VENV_DIR=venv
ZENDEV_REPO=git@github.com:zenoss/zendev.git
ZENDEV_DIR=zendev
ZENDEV_BRANCH=zendev2
ZENDEV_ENV=awesome-zendev-env
GO_VER=1.7.4
BRANCH=develop
REPO_NAME=zenoss-prodbin
REPO_PATH=$WORKSPACE/${ZENDEV_ENV}/src/github.com/zenoss/${REPO_NAME}

echo Creating a virtual env...
virtualenv ${VENV_DIR}
source ${VENV_DIR}/bin/activate
git clone ${ZENDEV_REPO} ${ZENDEV_DIR}
cd ${ZENDEV_DIR};git checkout ${ZENDEV_BRANCH}
pip install -e .

echo Use go version ${GO_VER}
source $GVM_ROOT/scripts/gvm
gvm use go${GO_VER}
GOPATH=$WORKSPACE/goworld go get github.com/iancmcc/jig

source $(zendev bootstrap)

echo Creating a zendev environment...
cd $WORKSPACE
zendev init --tag $BRANCH ${ZENDEV_ENV}
zendev use ${ZENDEV_ENV}

# The Jenkins project is configured to checkout to a sub-directory named
# REPO_NAME. Copy this to the zendev environment created above.
rm -rf ${REPO_PATH}
cp -r $WORKSPACE/${REPO_NAME} ${REPO_PATH}

echo Creating a devimg...
zendev devimg --clean

echo Running tests...
zendev test --no-tty -- --no-zenpacks || echo "Test failed.";exit 1
