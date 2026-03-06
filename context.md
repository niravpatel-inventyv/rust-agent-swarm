PROJECT: Autonomous Rust Development Agent Team

Goal
----
Build a multi-agent system that can autonomously develop a Rust backend project using local LLMs.

Agents collaborate through shared files in a Git repository.

The system should behave like an engineering team:
Architect → Lead → Developer(s) → Tester → Lead → Commit/PR

Models run locally via Ollama.


Current State
-------------

Git branch: dev
Last clean commit: df64f55 (Add initial project structure and agent implementations)
Agent fix commit: a27fdbd (Fix all agent implementations)
Remote: origin/dev is up to date with agent fixes force-pushed.

The Rust project at src/ is currently a stub (Hello World in main.rs).
No modules have been implemented yet — agents are ready to generate them.


System Architecture
-------------------

Agents:

1. Architect (agents/architect.py)
2. Lead (agents/lead.py)
3. Developer (agents/developer.py)
4. Tester (agents/tester.py)
5. Orchestrator (orchestrator.py) — coordinates the full pipeline


Orchestration Flow (with retry loops)
--------------------------------------

PHASE 1: ARCHITECTURE (loops up to 3x)

  1. Architect reads feature_request.txt
  2. Architect calls LLM (llama3:8b) to design architecture
  3. Architect writes contracts/api-spec.md and tasks/TASKS.md
  4. Lead reviews architecture (lead_review_architecture)
  5. If REJECTED → Architect reads rejection feedback and calls revise_plan()
  6. Loop back to step 4 (up to MAX_ARCHITECTURE_RETRIES=3)
  7. If APPROVED → proceed to Phase 2

PHASE 2: DEVELOPMENT

  1. Developer reads TASKS.md, finds unclaimed [ ] tasks
  2. Developer claims task ([ ] → [DEV])
  3. Developer calls LLM (deepseek-coder:6.7b) with CLAUDE.md rules + api-spec + existing code
  4. Developer parses FILE:/CODE: blocks from LLM output
  5. Developer writes .rs files to src/modules/<module>/
  6. Developer runs cargo build
  7. If build fails → self_heal() re-prompts LLM with error output
  8. Developer marks task [TEST] and writes to PROGRESS.md
  9. Repeat for all tasks

PHASE 3: TESTING

  1. Tester reads all src/ files
  2. Tester calls LLM to generate Rust test code
  3. Tester extracts ```rust blocks from LLM output
  4. Tester writes tests/generated_tests.rs
  5. Tester runs cargo test
  6. Tester writes reports/test-report.md with pass/fail counts

PHASE 4: CODE REVIEW (loops up to 3x)

  1. Lead reviews all src/ code (lead_review_code)
  2. If REJECTED → Lead provides REFACTOR_INSTRUCTIONS
  3. Developer reads feedback, calls refactor_code()
  4. Developer modifies files, runs cargo build
  5. Tester re-runs tests
  6. Loop back to step 1 (up to MAX_CODE_REVIEW_RETRIES=3)
  7. If APPROVED → orchestration complete


Agent Details
-------------

Architect (agents/architect.py):

  Functions:
    architect_plan(feature_request) — initial architecture design
    revise_plan(feature, rejection_feedback, session_number) — revise after rejection
    _update_tasks_file(task_lines) — writes TASKS.md with proper format

  Model: llama3:8b
  Reads: CLAUDE.md, feature_request.txt, tasks/TASKS.md
  Writes: contracts/api-spec.md, tasks/TASKS.md
  Does NOT write code.


Lead (agents/lead.py):

  Functions:
    lead_review_architecture(session_number) — review arch spec, returns (decision, is_approved)
    lead_review_code(session_number) — review source code, returns (decision, is_approved, refactor_feedback)
    _get_session_number() — auto-increment session counter from APPROVALS.md

  Model: llama3:8b
  Reads: CLAUDE.md, contracts/api-spec.md, tasks/TASKS.md, tasks/PROGRESS.md,
         tasks/BLOCKED.md, reports/test-report.md, tasks/APPROVALS.md, src/**/*.rs
  Writes: tasks/APPROVALS.md (append only, never overwrite)

  Review sessions are numbered and labeled:
    # REVIEW SESSION 1 — ARCHITECTURE REVIEW
    # REVIEW SESSION 2 — ARCHITECTURE REVIEW
    # REVIEW SESSION 3 — CODE REVIEW

  Does NOT write code.


Developer (agents/developer.py):

  Functions:
    implement_task(task_name) — implement a task, write Rust files, run cargo build
    refactor_code(refactor_feedback, session_number) — refactor based on Lead feedback
    self_heal(task_name, build_error, file_paths) — re-prompt LLM to fix build errors
    get_unclaimed_tasks() — find [ ] tasks in TASKS.md
    claim_task(task_name) — mark [ ] → [DEV]
    complete_task(task_name) — mark [DEV] → [TEST]
    parse_file_blocks(llm_output) — extract FILE:/CODE: blocks from LLM text
    get_existing_rust_code() — read all src/**/*.rs files

  Model: deepseek-coder:6.7b
  Reads: CLAUDE.md, contracts/api-spec.md, tasks/TASKS.md, tasks/BLOCKED.md, src/**/*.rs
  Writes: src/**/*.rs, tasks/TASKS.md (status updates), tasks/PROGRESS.md, tasks/BLOCKED.md


Tester (agents/tester.py):

  Functions:
    generate_tests() — generate test code, run cargo test, write report
    extract_test_code(llm_output) — parse ```rust blocks from LLM output
    get_source_code() — read all src/**/*.rs

  Model: deepseek-coder:6.7b
  Reads: CLAUDE.md, contracts/api-spec.md, tasks/PROGRESS.md, src/**/*.rs
  Writes: tests/generated_tests.rs, reports/test-report.md, tasks/TASKS.md ([TEST] → [DONE])


Orchestrator (orchestrator.py):

  Constants:
    MAX_ARCHITECTURE_RETRIES = 3
    MAX_CODE_REVIEW_RETRIES = 3

  Imports from agents/ via sys.path manipulation.
  Coordinates the 4-phase pipeline with retry loops.


Coordination Files
------------------

tasks/TASKS.md
  Task board. Format: [ ] / [DEV] / [TEST] / [DONE] prefix per task line.

tasks/APPROVALS.md
  Append-only log of all review sessions.
  Format per entry: request_by / type / description / decision / approved_by / reason

tasks/PROGRESS.md
  Append-only log of completed work.
  Format: agent / task / description / files_modified

tasks/BLOCKED.md
  Log of blocked tasks.
  Format: agent / task / problem / attempted_solution / status

tasks/DECISIONS.md
  Architecture decisions log.

reports/test-report.md
  Test results: status / tests_run / tests_passed / tests_failed / output

contracts/api-spec.md
  API specification written by Architect, reviewed by Lead.


Repository Structure
--------------------

project-root/
  CLAUDE.md                    — project rules, architecture, coding conventions
  context.md                   — this file (system context for agents/chats)
  feature_request.txt          — input feature to build
  orchestrator.py              — main entry point: python3 orchestrator.py
  agents/
    architect.py
    developer.py
    lead.py
    tester.py
  contracts/
    api-spec.md
  tasks/
    TASKS.md
    APPROVALS.md
    PROGRESS.md
    BLOCKED.md
    DECISIONS.md
    ISSUES.md
    LIMITS.md
  reports/
    test-report.md
  src/
    main.rs                    — currently stub, agents will populate
    modules/                   — agents create modules here
  tests/
    generated_tests.rs         — tester writes tests here
  Cargo.toml                   — protected, needs Lead approval to modify


Technology Stack
----------------

Rust: Axum, Tokio, SQLx, Serde
Database: PostgreSQL
LLMs: Ollama (llama3:8b for Architect/Lead, deepseek-coder:6.7b for Developer/Tester)
Agent runtime: Python 3


Coding Rules (from CLAUDE.md)
------------------------------

- Modular monolith: src/modules/<name>/ with mod.rs, model.rs, service.rs, repository.rs, handlers.rs
- No unwrap() in production code
- Use Result<T, AppError> for error handling
- API response format: { "data": T, "error": null }
- Always validate input
- Never log sensitive data
- Hash passwords
- Protected files (need Lead approval): Cargo.toml, .env, src/db/migrations


Known Issues / Notes
--------------------

- LLM output parsing is best-effort. Small models (6-8B) sometimes produce
  malformed FILE:/CODE: blocks or invalid Rust. The self-heal loop helps but
  is not guaranteed to fix all issues.

- The architect sometimes fails to produce task lines in [ ] format.
  A fallback parser looks for action keywords (implement, create, add, etc).

- APPROVALS.md session numbering is auto-incremented by counting existing
  "# REVIEW SESSION" headers.

- Tests skip if no real implementation exists in src/ (only Hello World main.rs).

- Parallel developer workers are supported but not yet wired in the orchestrator.
  The standalone run_developer() loop in developer.py supports this.


How to Run
----------

  python3 orchestrator.py

This runs the full pipeline: Architect → Lead → Developer → Tester → Lead
with retry loops on rejection.