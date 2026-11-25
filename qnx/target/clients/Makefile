#
# RIFT-QNX client workload Makefile (QNX SDP 8.0, x86_64).
#
# Build on a QNX SDP 8.0 development host: make
#

QNX_TARGET ?=

CC = qcc -Vgcc_ntox86_64

CFLAGS += -O2 -Wall -Wextra -Iinclude
LDFLAGS += -lsocket

TARGET = load_client
SRCS = src/load_client.c
OBJS = $(SRCS:.c=.o)

.PHONY: all clean check-toolchain

all: check-toolchain $(TARGET)

check-toolchain:
	@if ! command -v qcc >/dev/null 2>&1; then \
		echo "ERROR: qcc not found on PATH. Source the QNX SDP 8.0 environment."; \
		exit 2; \
	fi

$(TARGET): $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $(OBJS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)
