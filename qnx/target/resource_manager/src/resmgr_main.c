#include "resmgr_main.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <errno.h>
#include <sys/neutrino.h>
#include <sys/iomsg.h>

/* Compiled-in handler mode: MODE_BLOCKING or MODE_DEFERRED. */
int g_resmgr_mode = MODE_BLOCKING;

/* Thread-pool attributes. */
int g_lo_water     = DEFAULT_LO_WATER;
int g_increment    = DEFAULT_INCREMENT;
int g_hi_water     = DEFAULT_HI_WATER;
int g_maximum      = DEFAULT_MAXIMUM;
int g_worker_priority = 10;
unsigned g_worker_stack_size = 512 * 1024;

/* Report worker state (instrumentation hook for observability). */
void resmgr_report_worker_state(int tid, const char *state) {
    /* Intentionally minimal on target: a no-op here keeps the resource
       manager free of host dependencies. The host analyzer derives worker
       states from QNX kernel trace events (THREAD/COMM classes). */
    (void)tid;
    (void)state;
}

/* Simulated slow device operation inside a worker handler.
   Blocks the calling worker for the given nanoseconds. */
static void slow_device_op(struct timespec *dur) {
    if (dur) {
        nanosleep(dur, NULL);
    }
}

/* ---- Version A: blocking handler ---- */
/* Handler performs a slow synchronous operation inside the worker,
   holding the worker and draining the receive reserve. */
int blocking_handler(resmgr_context_t *ctp, io_read_t *msg, void *handle) {
    struct timespec block_dur = { .tv_sec = 0, .tv_nsec = 250000000 }; /* 250 ms */

    resmgr_report_worker_state(ThreadCtl(_NTO_TCTL_THREAD, NULL) == -1 ? -1 : 0, "BLOCKING_HANDLER");

    /* Simulate waiting for device data while this worker stays occupied. */
    slow_device_op(&block_dur);

    /* Reply with a small payload. */
    iofunc_read_default(ctp, msg, handle);
    return _RESMGR_NOREPLY;
}

/* ---- Version B: deferred completion ---- */
/* Pending reply table keyed by rcvid. */
#define MAX_PENDING 256

typedef struct {
    int rcvid;
    int coid;                 /* client connection id */
    int ready;
    int result;
    struct timespec reply_at;
} pending_entry_t;

static pending_entry_t g_pending[MAX_PENDING];
static pthread_mutex_t g_pending_lock = PTHREAD_MUTEX_INITIALIZER;

/* Completion worker: simulates device completion and replies via MsgReply. */
static void *completion_worker(void *arg) {
    (void)arg;
    for (;;) {
        int i;
        int rcvid = -1;

        pthread_mutex_lock(&g_pending_lock);
        for (i = 0; i < MAX_PENDING; i++) {
            if (g_pending[i].ready && g_pending[i].rcvid >= 0) {
                rcvid = g_pending[i].rcvid;
                g_pending[i].rcvid = -1;
                g_pending[i].ready = 0;
                break;
            }
        }
        pthread_mutex_unlock(&g_pending_lock);

        if (rcvid >= 0) {
            /* Simulate device completing the operation. */
            struct timespec device_lat = { .tv_sec = 0, .tv_nsec = 50000000 }; /* 50 ms */
            nanosleep(&device_lat, NULL);

            /* Reply to the waiting client. */
            int status = MsgReply(rcvid, EOK, NULL, 0);
            (void)status;
        } else {
            /* Nothing pending; sleep briefly to avoid spinning. */
            struct timespec idle = { .tv_sec = 0, .tv_nsec = 5000000 }; /* 5 ms */
            nanosleep(&idle, NULL);
        }
    }
    return NULL;
}

static pthread_t g_completion_tid;

int deferred_handler(resmgr_context_t *ctp, io_read_t *msg, void *handle) {
    int rcvid = ctp->rcvid;
    int i;

    /* 1. Save the receive id (rcvid). */
    /* 2. Place pending operation in thread-safe queue. */
    pthread_mutex_lock(&g_pending_lock);
    for (i = 0; i < MAX_PENDING; i++) {
        if (g_pending[i].rcvid < 0) {
            g_pending[i].rcvid = rcvid;
            g_pending[i].coid = ctp->scoid ? ctp->scoid : 0;
            g_pending[i].ready = 0;
            g_pending[i].result = EOK;
            break;
        }
    }
    pthread_mutex_unlock(&g_pending_lock);

    if (i == MAX_PENDING) {
        /* Queue full: cannot accept now. */
        return EAGAIN;
    }

    /* 3. Return _RESMGR_NOREPLY so the worker returns to RECEIVE. */
    resmgr_report_worker_state(0, "RECEIVE_READY");
    return _RESMGR_NOREPLY;
}

/* ---- IO funcs / connect funcs ---- */

static int resmgr_open(resmgr_context_t *ctp, io_open_t *msg,
                       void *handle, void *extra) {
    (void)handle; (void)extra;
    return iofunc_open_default(ctp, msg, NULL, NULL, extra);
}

static int resmgr_read(resmgr_context_t *ctp, io_read_t *msg, void *handle) {
    if (g_resmgr_mode == MODE_BLOCKING) {
        return blocking_handler(ctp, msg, handle);
    } else {
        return deferred_handler(ctp, msg, handle);
    }
}

static int resmgr_write(resmgr_context_t *ctp, io_write_t *msg, void *handle) {
    (void)handle;
    /* Accept write, reply immediately (no blocking). */
    iofunc_write_default(ctp, msg, handle);
    return _RESMGR_NOREPLY;
}

static int resmgr_unlink(resmgr_context_t *ctp, io_unlink_t *msg,
                         void *handle, void *extra) {
    (void)handle; (void)extra;
    return iofunc_unlink_default(ctp, msg, NULL, extra);
}

/* IO funcs table. */
static iofunc_funcs_t resmgr_io_funcs = {
    _IOFUNCS_NFUNCS,
    resmgr_open,       /* open */
    0,                 /* close_ocb */
    0,                 /* stat */
    resmgr_read,       /* read */
    resmgr_write,      /* write */
    0,                 /* lseek */
    resmgr_unlink,     /* unlink */
};

/* Connect funcs table. */
static iofunc_connect_t resmgr_connect_funcs = {
    _IOFUNCS_NFUNCS,
    resmgr_open,
};

int main(int argc, char **argv) {
    name_attach_t *attach;
    dispatch_t *dpp;
    thread_pool_attr_t pool_attr;
    thread_pool_t *tpp;
    int opt;
    int flags = 0;

    /* Parse overrides from command line (for scenario testing). */
    while ((opt = getopt(argc, argv, "m:l:i:h:x:p:s:")) != -1) {
        switch (opt) {
        case 'm': g_resmgr_mode = atoi(optarg) ? MODE_DEFERRED : MODE_BLOCKING; break;
        case 'l': g_lo_water = atoi(optarg); break;
        case 'i': g_increment = atoi(optarg); break;
        case 'h': g_hi_water = atoi(optarg); break;
        case 'x': g_maximum = atoi(optarg); break;
        case 'p': g_worker_priority = atoi(optarg); break;
        case 's': g_worker_stack_size = (unsigned)atoi(optarg); break;
        }
    }

    /* Create a channel for the resource manager. */
    attach = name_attach(NULL, RESMGR_ATTACH_NAME, 0);
    if (!attach) {
        fprintf(stderr, "rift_resmgr: name_attach failed: %s\n", strerror(errno));
        return EXIT_FAILURE;
    }
    dpp = attach->dispatch;

    if (g_resmgr_mode == MODE_DEFERRED) {
        /* Start the deferred completion worker. */
        if (pthread_create(&g_completion_tid, NULL, completion_worker, NULL) != 0) {
            fprintf(stderr, "rift_resmgr: pthread_create completion_worker failed\n");
            return EXIT_FAILURE;
        }
    }

    /* Initialize iofunc tables. */
    iofunc_func_init(_RESMGR_CONNECT_NFUNCS, &resmgr_connect_funcs);
    iofunc_func_init(_RESMGR_IO_NFUNCS, &resmgr_io_funcs);

    /* Configure the thread pool. */
    memset(&pool_attr, 0, sizeof pool_attr);
    pool_attr.handle = dpp;
    pool_attr.context_alloc = dispatch_context_alloc;
    pool_attr.block_func = dispatch_block;
    pool_attr.handler_func = dispatch_handler;
    pool_attr.lo_water = g_lo_water;
    pool_attr.increment = g_increment;
    pool_attr.hi_water = g_hi_water;
    pool_attr.maximum = g_maximum;
    pool_attr.attr = NULL; /* default thread attributes */

    tpp = thread_pool_create(&pool_attr, POOL_FLAG_EXIT_SELF);
    if (!tpp) {
        fprintf(stderr, "rift_resmgr: thread_pool_create failed: %s\n", strerror(errno));
        return EXIT_FAILURE;
    }

    fprintf(stderr, "rift_resmgr: started mode=%d lo=%d inc=%d hi=%d max=%d\n",
            g_resmgr_mode, g_lo_water, g_increment, g_hi_water, g_maximum);

    /* Start serving. Never returns on success. */
    thread_pool_start(tpp);

    return EXIT_FAILURE;
}
