#
# RIFT-QNX resource manager Makefile (QNX SDP 8.0, x86_64).
#
# Build on a supported QNX development host (x86_64 Linux/Windows) with
# QNX SDP 8.0 installed. Run: make
#
# The QNX toolchain (qcc, ntox86-*) is NOT available on macOS/ARM hosts.
# This Makefile targets x86_64 QNX; on a host without QNX SDP it will
# report the missing toolchain rather than silently produce a bad binary.
#

QNX_TARGET ?=
QNX_HOST    ?=

CC = qcc -Vgcc_ntox86_64
LD = $(CC)

INCLUDES += -Iinclude

CFLAGS += -O2 -Wall -Wextra $(INCLUDES)
LDFLAGS += -lsocket

TARGET = rift_resmgr
SRCS = src/resmgr_main.c
OBJS = $(SRCS:.c=.o)

.PHONY: all clean block defer run install check-toolchain

all: check-toolchain $(TARGET)

check-toolchain:
	@if ! command -v qcc >/dev/null 2>&1; then \
		echo "ERROR: qcc not found on PATH. Source the QNX SDP 8.0 environment."; \
		echo "  . /path/to/qnx800/qnxsdp-8.0.0/qnxsdp-env.sh"; \
		exit 2; \
	fi

$(TARGET): $(OBJS)
	$(LD) $(LDFLAGS) -o $@ $(OBJS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# Build Version A (blocking handler, the faulty baseline).
block: CFLAGS += -DDEFAULT_MODE_BLOCKING
block: check-toolchain $(TARGET)

# Build Version B (deferred reply, the corrected design).
defer: CFLAGS += -DDEFAULT_MODE_DEFERRED
defer: check-toolchain $(TARGET)

clean:
	rm -f $(OBJS) $(TARGET)

run: $(TARGET)
	qnxrun -t ntox86-$(TARGET) $(TARGET)

install: $(TARGET)
	install -m 755 $(TARGET) /usr/bin/
