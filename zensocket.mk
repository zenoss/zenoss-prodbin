#
# Makefile for zensocket
#
.PHONY: clean-zensocket build-zensocket

CC      := gcc
CFLAGS  := -Wall -pedantic -D__GNU_LIBRARY__ -g
LDFLAGS :=

ZENSOCKET_BINARY := bin/zensocket
ZENSOCKET_SRC := legacy/zensocket/zensocket.c

clean-zensocket:
	rm -rf $(ZENSOCKET_BINARY)

build-zensocket: $(ZENSOCKET_BINARY)

$(ZENSOCKET_BINARY): $(ZENSOCKET_SRC)
ifeq ($(DOCKER),)
	$(CC) -o $@ $(CFLAGS) $(LDFLAGS) $(ZENSOCKET_SRC)
else
	$(DOCKER_RUN) "$(CC) -o $@ $(CFLAGS) $(LDFLAGS) $(ZENSOCKET_SRC)"
endif
