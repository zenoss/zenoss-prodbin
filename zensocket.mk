#
# Makefile for zensocket
#
.PHONY: clean-zensocket build-zensocket

CC      := gcc
CFLAGS  := -Wall -pedantic -D__GNU_LIBRARY__ -g
LDFLAGS :=

ZENSOCKET_BINARY := bin/zensocket
ZENSOCKET_SRC := legacy/zensocket/zensocket.c

UID := $(shell id -u)
GID := $(shell id -g)

#
# FIXME: the following logic needs to be somewhere such the file ownership/perms
#        on the binary looks like:
#-rwsr-x--- 1 root zenoss <size> <date> /opt/zenoss/bin/zensocket
#
# chown root $@; chmod uog+rx,u+ws $@"

clean-zensocket:
	rm -rf $(ZENSOCKET_BINARY)

build-zensocket: $(ZENSOCKET_BINARY)

$(ZENSOCKET_BINARY): $(ZENSOCKET_SRC)
	cd legacy/zensocket && \
	docker run --rm \
		-v $(PWD):/mnt \
		--user $(UID):$(GID) \
		$(BUILD_IMAGE_TAG) \
		/bin/bash -c \
		"cd /mnt && $(CC) -o $@ $(CFLAGS) $(LDFLAGS) $(ZENSOCKET_SRC)"
