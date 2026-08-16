#include <stdio.h>
#include <stdlib.h>
#include "TaskScheduler_c.h"
#include "task_scheduler.h"
#include "box2d/box2d.h"

// Global task scheduler pointer and thread count.
static enkiTaskScheduler* g_taskScheduler = NULL;
static unsigned int g_numThreads = 0;

/*
 * Box2D 3.2 reworked threading. A b2TaskCallback is now a single opaque unit of
 * work, "void task(void* context)", instead of the old range callback that took
 * (start, end, worker, context) and expected the scheduler to split it. Box2D
 * does the splitting itself now and hands us finished pieces.
 *
 * enkiTS still wants a range function, so each task is wrapped in a one-element
 * task set whose range function calls the real callback exactly once.
 */
typedef struct
{
    b2TaskCallback* task;
    void* taskContext;
} TaskWrapper;

static void run_wrapped_task(uint32_t start, uint32_t end, uint32_t threadNum, void* args)
{
    (void)start;
    (void)end;
    (void)threadNum;
    TaskWrapper* wrapper = (TaskWrapper*)args;
    wrapper->task(wrapper->taskContext);
}

/*
 * setup_threadpool
 *
 * Initializes the task scheduler with the specified number of threads.
 */
void setup_threadpool(unsigned int num_threads)
{
    if (g_taskScheduler != NULL)
    {
        printf("Task scheduler is already initialized.\n");
        return;
    }
    g_taskScheduler = enkiNewTaskScheduler();
    if (!g_taskScheduler)
    {
        fprintf(stderr, "Error: Unable to create enkiTaskScheduler!\n");
        return;
    }
    enkiInitTaskSchedulerNumThreads(g_taskScheduler, num_threads);
    g_numThreads = num_threads;
}

/*
 * c_enqueue_tasks
 *
 * Schedules one Box2D task on the pool.
 *
 * Returns:
 *   An opaque pointer (task set) if the task was scheduled, or NULL if it ran
 *   inline because no scheduler is available.
 */
void* c_enqueue_tasks(b2TaskCallback* task, void* taskContext, void* userContext)
{
    (void)userContext;

    if (g_taskScheduler == NULL)
    {
        // No pool: running inline is still correct, just serial.
        task(taskContext);
        return NULL;
    }

    TaskWrapper* wrapper = (TaskWrapper*)malloc(sizeof(TaskWrapper));
    if (wrapper == NULL)
    {
        task(taskContext);
        return NULL;
    }
    wrapper->task = task;
    wrapper->taskContext = taskContext;

    enkiTaskSet* pTaskSet = enkiCreateTaskSet(g_taskScheduler, run_wrapped_task);
    if (pTaskSet == NULL)
    {
        free(wrapper);
        task(taskContext);
        return NULL;
    }

    enkiSetSetSizeTaskSet(pTaskSet, 1);
    enkiSetArgsTaskSet(pTaskSet, wrapper);
    enkiAddTaskSet(g_taskScheduler, pTaskSet);

    return pTaskSet;
}

/*
 * c_finish_tasks
 *
 * Waits for the provided task set to complete, then releases it along with its
 * wrapper. A NULL taskSet means the work already ran inline.
 */
void c_finish_tasks(void *taskSet, void *userContext)
{
    (void)userContext;

    if (taskSet == NULL) return;

    enkiTaskSet* pTaskSet = (enkiTaskSet*)taskSet;
    enkiWaitForTaskSet(g_taskScheduler, pTaskSet);

    // The previous implementation waited but never released either the wrapper
    // or the task set, leaking both on every step.
    struct enkiParamsTaskSet params = enkiGetParamsTaskSet(pTaskSet);
    free(params.pArgs);
    enkiDeleteTaskSet(g_taskScheduler, pTaskSet);
}

/*
 * cleanup_threadpool
 *
 * Cleans up the task scheduler by shutting down active tasks and deleting the scheduler.
 */
void cleanup_threadpool()
{
    if (g_taskScheduler != NULL)
    {
        enkiWaitforAllAndShutdown(g_taskScheduler);
        enkiDeleteTaskScheduler(g_taskScheduler);
        g_taskScheduler = NULL;
        g_numThreads = 0;
    }
}
