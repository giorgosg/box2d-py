#include "box2d/box2d.h"

// Initializes the task scheduler with the specified number of worker threads.
__attribute__((visibility("default"))) void setup_threadpool(unsigned int num_threads);

// Enqueues a task to be executed with the given parameters.
// Returns an opaque pointer (handle) to the task set.
__attribute__((visibility("default"))) void* c_enqueue_tasks(
    b2TaskCallback* task, 
    int itemCount, 
    int minRange, 
    void *taskContext, 
    void *userContext);
// Waits for the enqueued task set to complete and then deletes the task set.
__attribute__((visibility("default"))) void c_finish_tasks(void *taskSet, void *userContext);

// Cleans up and shuts down the task scheduler.
__attribute__((visibility("default"))) void cleanup_threadpool();
