VERSION  := 5.2.0
BRANCH   := develop
ARTIFACT := prodbin-$(VERSION)-$(BRANCH).tar.gz

.PHONY: all clean build javascript

all: build

build: javascript
	tar cvfz $(ARTIFACT) Products bin

javascript:
	make -f javascript.mk build

clean:
	rm -f $(ARTIFACT)
	-make -f javascript.mk clean
