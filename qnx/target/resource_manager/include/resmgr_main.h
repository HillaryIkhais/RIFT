#ifndef RESMGR_MAIN_H
#define RESMGR_MAIN_H

#include <sys/iofunc.h>
#include <sys/dispatch.h>

/* Resource manager path served by this process. */
#define RESMGR_PATH "/dev/rift_resmgr"

/* Attached name (may differ from mount path). */
#define RESMGR_ATTACH_NAME "rift_resmgr"

/* Handler implementation mode, compiled in at build time. */
enum resmgr_mode {
    MODE_BLOCKING,   /* Version A: synchronous blocking inside handler */
    MODE_DEFERRED,   /* Version B: deferred completion via MsgReply */
};

extern int g_resmgr_mode;
extern int g_lo_water;
extern int g_increment;
extern int g_hi_water;
extern int g_maximum;
extern int g_worker_priority;
extern unsigned g_worker_stack_size;

/* Default thread-pool configuration for the faulty baseline scenario. */
#define DEFAULT_LO_WATER     1
#define DEFAULT_INCREMENT    1
#define DEFAULT_HI_WATER     4
#define DEFAULT_MAXIMUM      4

/* Instrumentation hook: reports current worker state to a side channel
   (host-side analyzer reads the process state / trace). */
void resmgr_report_worker_state(int tid, const char *state);

#endif
