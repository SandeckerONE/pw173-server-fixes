# Makefile for treasure_hook. The 1.7.3 gs is a 32-bit program, so the real
# library MUST be built 32-bit (the default target here).
#
#   make            build libtreasure.so (32-bit) for the server
#   make install    copy it + a starter config into /opt/treasure_hook (needs sudo)
#   make clean
#
# 32-bit build needs the multilib compiler:  sudo apt install -y gcc-multilib
CC      ?= gcc
CFLAGS  := -m32 -std=gnu11 -O2 -fPIC -shared -mstackrealign \
           -fvisibility=hidden -Wall -Wextra -D_FILE_OFFSET_BITS=64
LIBS    := -ldl -lpthread
OUT     := libtreasure.so
PREFIX  ?= /opt/treasure_hook

$(OUT): treasure_hook.c
	$(CC) $(CFLAGS) -o $@ $< $(LIBS)
	@echo "built $@ :"; file $@

# the server runs 64-bit only if you ever move to a 64-bit gs; not used on 1.7.3
lib64:
	$(CC) -std=gnu11 -O2 -fPIC -shared -fvisibility=hidden -Wall -Wextra \
	      -o libtreasure64.so treasure_hook.c $(LIBS)

install: $(OUT)
	install -d $(PREFIX) $(PREFIX)/state
	install -m 0644 $(OUT) $(PREFIX)/$(OUT)
	@if [ -f $(PREFIX)/treasure_hook.conf ]; then \
	   echo "kept existing $(PREFIX)/treasure_hook.conf"; \
	 elif [ -f ../conf/treasure_hook.conf ]; then \
	   install -m 0644 ../conf/treasure_hook.conf $(PREFIX)/treasure_hook.conf; \
	   echo "installed starter config $(PREFIX)/treasure_hook.conf"; \
	 fi
	@echo "installed to $(PREFIX). It does nothing until the /opt/server gs line is changed; see README.md."

clean:
	rm -f $(OUT) libtreasure64.so

.PHONY: install clean lib64
