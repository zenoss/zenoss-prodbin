VERSION ?= 5.2.0
BRANCH ?= develop

.PHONY: all
all: tar

tar:
	tar cfz prodbin-$(BRANCH)-$(VERSION).tar.gz Products bin