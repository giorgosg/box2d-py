#ifndef TASK_SCHEDULER_H
#define TASK_SCHEDULER_H

#include "box2d/box2d.h"

#ifdef _WIN32
    #define API_EXPORT __declspec(dllexport)
#else
    #define API_EXPORT __attribute__((visibility("default")))
#endif

// Initializes the task scheduler with the specified number of worker threads.
API_EXPORT void setup_threadpool(unsigned int num_threads);

// Enqueues a task to be executed with the given parameters.
// Returns an opaque pointer (handle) to the task set.
API_EXPORT void* c_enqueue_tasks(
    b2TaskCallback* task, 
    int itemCount, 
    int minRange, 
    void *taskContext, 
    void *userContext);

// Waits for the enqueued task set to complete and then deletes the task set.
API_EXPORT void c_finish_tasks(void *taskSet, void *userContext);

// Cleans up and shuts down the task scheduler.
API_EXPORT void cleanup_threadpool();

#endif // TASK_SCHEDULER_H
