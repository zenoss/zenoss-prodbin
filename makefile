include version.mk
include javascript.mk
include migration.mk

BUILD_IMAGE = zenoss/prodbin-build

.DEFAULT_GOAL := build

.PHONY: build
build:
	@docker build --no-cache --progress=plain --pull -t $(BUILD_IMAGE) .
	@docker run --rm -v $(shell pwd):/work -w /work $(BUILD_IMAGE) make -f wheel.mk

.PHONY: clean
clean: clean-javascript clean-migration
	@make -f wheel.mk clean-wheel

.PHONY: test
test:
	@make -C ci
