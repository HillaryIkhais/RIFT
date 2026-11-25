#include "load_client.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <errno.h>
#include <sys/neutrino.h>
#include <sys/dispatch.h>
#include <sys/iomsg.h>

static long now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long)ts.tv_sec * 1000000000L + ts.tv_nsec;
}

void workload_run(client_stats_t *stats) {
    int coid = name_open(RESMGR_PATH, 0);
    if (coid == -1) {
        fprintf(stderr, "client %d: name_open %s failed: %s\n",
                stats->client_id, RESMGR_PATH, strerror(errno));
        stats->failures++;
        return;
    }

    char *buf = malloc(stats->op_len ? stats->op_len : DEFAULT_OP_LEN);
    if (!buf) {
        fprintf(stderr, "client %d: malloc failed\n", stats->client_id);
        stats->failures++;
        ConnectDetach(coid);
        return;
    }
    memset(buf, 'R', stats->op_len ? stats->op_len : DEFAULT_OP_LEN);

    int i;
    for (i = 0; i < stats->request_count; i++) {
        long t0 = now_ns();
        int status = MsgSend(coid, buf, stats->op_len ? stats->op_len : DEFAULT_OP_LEN,
                             buf, stats->op_len ? stats->op_len : DEFAULT_OP_LEN);
        long t1 = now_ns();

        if (status == -1) {
            stats->failures++;
            continue;
        }

        long latency = t1 - t0;
        if (stats->latency_count < stats->request_count) {
            stats->latencies_ns[stats->latency_count++] = (int)latency;
        }

        /* Approximation of SEND-blocking: latency far above the local
           processing floor indicates the client waited on the server. */
        if (stats->response_budget_ns > 0 && latency > stats->response_budget_ns) {
            stats->send_blocked_count++;
        }
    }

    free(buf);
    ConnectDetach(coid);
}

/* Standalone mode: run one client against the resource manager for smoke testing. */
int main(int argc, char **argv) {
    int c;
    client_stats_t stats;
    memset(&stats, 0, sizeof stats);
    stats.client_id = 0;
    stats.request_count = DEFAULT_REQUESTS;
    stats.op_len = DEFAULT_OP_LEN;
    stats.concurrency = 1;
    stats.response_budget_ns = 100000000L; /* 100 ms */
    stats.latencies_ns = calloc(stats.request_count, sizeof(int));

    while ((c = getopt(argc, argv, "c:n:l:b:")) != -1) {
        switch (c) {
        case 'c': stats.client_id = atoi(optarg); break;
        case 'n': stats.request_count = atoi(optarg); break;
        case 'l': stats.op_len = atoi(optarg); break;
        case 'b': stats.response_budget_ns = atol(optarg); break;
        }
    }

    workload_run(&stats);

    printf("client %d: requests=%d failures=%d send_blocked_approx=%d latencies=%d\n",
           stats.client_id, stats.request_count, stats.failures,
           stats.send_blocked_count, stats.latency_count);

    free(stats.latencies_ns);
    return 0;
}
