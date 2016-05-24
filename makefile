VERSION ?= 5.2.0
BRANCH ?= develop

.PHONY: all
all: tar

tar:
	tar cfz prod-bin-$(BRANCH)-$(VERSION).tar.gz Products bin