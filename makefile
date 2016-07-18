VERSION  := 5.2.0
BRANCH   := develop
ARTIFACT := prodbin-$(VERSION)-$(BRANCH).tar.gz

# Define the name, version and tag name for the docker build image
# Note that build-tools is derived from zenoss-centos-base which contains JSBuilder
BUILD_IMAGE = build-tools
BUILD_VERSION = 0.0.3
BUILD_IMAGE_TAG = zenoss/$(BUILD_IMAGE):$(BUILD_VERSION)

.PHONY: all clean build javascript zensocket

include javascript.mk
include zensocket.mk

all: build

build: build-javascript build-zensocket
	tar cvfz $(ARTIFACT) Products bin

clean: clean-javascript clean-zensocket
	rm -f $(ARTIFACT)

