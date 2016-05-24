VERSION ?= 5.2.0
BRANCH ?= dev

.PHONY: all
all: tar

tar:
	tar cfz prod-bin-$(BRANCH)-$(VERSION)-$(BUILD_NUMBER).tar.gz Products bin