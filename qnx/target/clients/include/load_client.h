#ifndef LOAD_CLIENT_H
#define LOAD_CLIENT_H

/* RIFT-QNX concurrent client workload for resource-manager testing. */

#define RESMGR_PATH "/dev/rift_resmgr"
#define DEFAULT_CLIENTS 8
#define DEFAULT_REQUESTS 40
#define DEFAULT_OP_LEN 256

typedef struct {
    int client_id;
    int request_count;
    int op_len;            /* payload bytes per request */
    int concurrency;       /* outstanding requests per client */
    long response_budget_ns; /* per-request latency budget */
    int *latencies_ns;     /* per-request measured latency (ns) */
    int latency_count;
    int send_blocked_count;/* times this client entered SEND-blocked (approx) */
    int failures;          /* failed requests */
} client_stats_t;

void workload_run(client_stats_t *stats);

#endif
