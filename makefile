VERSION ?= 5.2.0
BRANCH ?= develop

.PHONY: all
all: tar

tar:
	tar cfz prodbin-$(VERSION)-$(BRANCH).tar.gz Products bin