#include <stdio.h>
#include "TaskScheduler_c.h"
#include "task_scheduler.h"
#include "box2d/box2d.h"

// Global task scheduler pointer and thread count.
static enkiTaskScheduler* g_taskScheduler = NULL;
static unsigned int g_numThreads = 0;

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
    // printf("Task scheduler initialized with %u threads.\n", num_threads);
}

/*
 * c_enqueue_tasks
 *
 * - If the work is very fine-grained (itemCount < minRange),
 *   the task is executed inline.
 * - Otherwise, it computes a chunk size (max(minRange, computed_chunk))
 *   based on g_numThreads and schedules the task set
 *
 * Returns:
 *   An opaque pointer (task set) if tasks are scheduled or NULL if executed inline.
 */
void* c_enqueue_tasks(b2TaskCallback* task, int itemCount, int minRange, void *taskContext, void *userContext)
{
    if (g_taskScheduler == NULL)
    {
        fprintf(stderr, "Error: Task scheduler is not initialized!\n");
        return NULL;
    }

    // Convert to enkiTS task function type
    enkiTaskExecuteRange pTaskFunc = (enkiTaskExecuteRange)task;

    if (itemCount < minRange)
    {
        // printf("Executing inline: %d items\n", itemCount);
        pTaskFunc(0, itemCount, 0, taskContext);
        return NULL;
    }

    enkiTaskSet* pTaskSet = enkiCreateTaskSet(g_taskScheduler, pTaskFunc);
    
    // Initialize parameters using C API functions
    enkiSetSetSizeTaskSet(pTaskSet, itemCount);
    enkiSetMinRangeTaskSet(pTaskSet, minRange);
    enkiSetArgsTaskSet(pTaskSet, taskContext);

    // Schedule with minimum range using proper C API
    enkiAddTaskSetMinRange(g_taskScheduler, pTaskSet, taskContext, itemCount, minRange);
    
    return pTaskSet;
}

/*
 * c_finish_tasks
 *
 * This function waits for the provided task set to complete
 * and then deletes it. If taskSet is NULL then it indicates that the work
 * was executed inline.
 */
void c_finish_tasks(void *taskSet, void *userContext)
{
    if (taskSet == NULL) return;

    // Wait for completion using C API
    enkiWaitForTaskSet(g_taskScheduler, (enkiTaskSet*)taskSet);
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
        // printf("Task scheduler cleaned up.\n");
    }
}