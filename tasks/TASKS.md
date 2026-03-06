# TASK BOARD

This file tracks all development tasks.

Rules:

1 Architect creates tasks
2 Lead reviews and approves tasks
3 Developer claims approved tasks
4 Tester verifies completed tasks
5 Lead approves final commit


--------------------------------------------------

# TASK STATUS

[ ] = not started  
[DEV] = claimed by developer  
[TEST] = ready for testing  
[DONE] = completed  


--------------------------------------------------

# TASK LIST

[ ] Design API models for tasks module
owner: architect
status: waiting for lead approval


[ ] Implement Axum HTTP server bootstrap
owner: developer
status: waiting for lead approval


[ ] Implement task repository
owner: developer
status: waiting for lead approval


[ ] Implement task service layer
owner: developer
status: waiting for lead approval


[ ] Add integration tests for task API
owner: tester
status: waiting for implementation


--------------------------------------------------

# CLAIMING TASKS

Developer must update task when starting work.

Example:

[DEV] Implement task repository
owner: developer
claimed_by: developer-agent


--------------------------------------------------

# COMPLETING TASKS

When developer finishes implementation:

[TEST] Implement task repository
ready_for: tester


--------------------------------------------------

# TEST VERIFIED TASKS

When tester validates:

[DONE] Implement task repository
verified_by: tester-agent