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

if [ "$1" != "--no-tests" ]; then
	source zenoss-prodbin/jenkins_test.sh
	echo Running the tests...
	pushd ${ZENDEV_ROOT}/src/github.com/zenoss/product-assembly
	export PRODUCT_IMAGE_ID=zendev/devimg:${ZENDEV_ENV}
	export MARIADB_IMAGE_ID=zendev/mariadb:${ZENDEV_ENV}
	export REDIS_IMAGE_ID=zenoss/redis:latest
	export RABBITMQ_IMAGE_ID=zenoss/rabbitmq:latest
	docker image pull ${REDIS_IMAGE_ID}
	docker image pull ${RABBITMQ_IMAGE_ID}
	./test_image.sh \
		--no-pull-images \
		--no-zenpacks \
		--mount ${HOME}/.m2:/home/zenoss/.m2 \
		--mount ${ZENDEV_ROOT}/zenhome:/opt/zenoss \
		--mount ${ZENDEV_ROOT}/var_zenoss:/var/zenoss \
		--mount ${ZENDEV_ROOT}/src/github.com/zenoss:/mnt/src \
		--env SRCROOT=/mnt/src
	popd
fi

echo Building the artifacts...
pushd ${WORKSPACE}/${REPO_NAME}
make 
# docker run --rm \
#     -v ${HOME}/.m2:/home/zenoss/.m2 \
#     -v ${ZENDEV_ROOT}/zenhome:/opt/zenoss \
#     -v ${ZENDEV_ROOT}/src/github.com/zenoss:/mnt/src \
#     -w /mnt/src/zenoss-prodbin \
#     --env BRANCH=${BRANCH} \
#     --env ZENHOME=/opt/zenoss \
#     --env SRCROOT=/mnt/src \
#     zendev/devimg:${ZENDEV_ENV} \
#     make clean build
