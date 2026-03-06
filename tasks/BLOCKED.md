# BLOCKED TASKS

This file records failed attempts or blockers.

Agents must read this file before starting work.

--------------------------------------------------

# BLOCKED ENTRY FORMAT

agent:
task:
problem:
attempted_solution:
status:


--------------------------------------------------

# EXAMPLES

agent: developer
task: Kafka event consumer
problem: dependency not approved
attempted_solution: tried adding rdkafka crate
status: waiting for lead approval


agent: tester
task: integration tests
problem: API server not starting
attempted_solution: cargo run shows missing config
status: unresolved