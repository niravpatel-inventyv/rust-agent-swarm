# Project: Rust Modular Monolith Task Platform

## Product Overview

This project is a Rust backend service implemented as a modular monolith.

The system provides:

- Task management APIs
- User authentication
- Task assignment
- Event notifications
- Audit logging

Primary users:

- internal engineering teams
- automation systems
- backend services
- developer tools

The backend exposes REST APIs that can be consumed by:

- web dashboards
- CLI tools
- automation services
- other backend services


--------------------------------------------------

# Architecture

The service follows a modular monolith architecture.

Properties:

- single deployable service
- strict module boundaries
- domain separation
- services communicate through defined interfaces

Modules must not directly access other modules' repositories.

All cross-module communication must go through service layers.


--------------------------------------------------

# Project Structure

src
  api
    HTTP route handlers

  modules
    domain modules

  services
    application services

  db
    database layer

  middleware
    shared middleware

  events
    domain events

  utils
    shared utilities


Each module follows this structure:

module_name
  mod.rs
  model.rs
  service.rs
  repository.rs
  handlers.rs


Example module:

src/modules/tasks

Responsibilities:

- domain models
- validation
- persistence interface
- service logic


--------------------------------------------------

# Agent Team

The system uses four agents working together.

Lead
Architect
Developer
Tester

Each agent has strict responsibilities.


--------------------------------------------------

# Lead Agent

The Lead is responsible for governance and approvals.

Responsibilities:

- review architecture plans
- approve or reject tasks
- approve dependency changes
- verify test results
- approve commits

The lead must ensure:

- architecture is respected
- module boundaries are enforced
- tests exist for new code

The lead never writes implementation code.

Lead approval is required before:

- modifying Cargo.toml
- changing database schema
- introducing new dependencies


--------------------------------------------------

# Architect Agent

The Architect defines system design.

Responsibilities:

- design architecture
- define API contracts
- define domain models
- break features into tasks

Architect must produce:

contracts/api-spec.md

Architect must update:

tasks/TASKS.md

Architect responsibilities include:

- defining module boundaries
- defining service interactions
- ensuring maintainable architecture

Architect must never implement code.


--------------------------------------------------

# Developer Agent

The Developer implements tasks.

Developer workflow:

1 Read CLAUDE.md
2 Read API contracts
3 Read TASKS.md
4 Check BLOCKED.md
5 Select an approved task
6 Implement the code

Developer must:

- follow modular monolith rules
- write production Rust code
- maintain module boundaries
- ensure code compiles

Developer must request approval if:

- dependency changes are required
- architecture changes are needed
- database schema changes are needed

You have access to filesystem tools.

Allowed operations:

create directories
create files
edit files
run cargo commands

Do not modify protected files:

Cargo.toml
.env
src/db/migrations

Developer logs blockers in:

tasks/BLOCKED.md

Developer logs progress in:

tasks/PROGRESS.md

Developer must never commit code directly.


--------------------------------------------------

# Tester Agent

The Tester validates the implementation.

Responsibilities:

- write integration tests
- validate API contracts
- test edge cases
- test concurrency

Tests must cover:

- success scenarios
- validation failures
- concurrency cases
- error scenarios

Tests must be written in:

tests/

Tester must generate report:

reports/test-report.md

Tester sends report to Lead.

Tester must never modify application code.


--------------------------------------------------

# Development Workflow

The development process follows this order.

Architect → Lead → Developer → Tester → Lead

Detailed steps:

Step 1 Architect Planning

Architect designs the feature.

Architect writes:

contracts/api-spec.md
tasks/TASKS.md


Step 2 Lead Review

Lead reviews architecture.

Lead may:

approve tasks
modify tasks
reject design


Step 3 Developer Implementation

Developer selects an approved task.

Developer implements code.

Developer runs verification commands.


Step 4 Testing Phase

Tester generates tests.

Tester runs full test suite.

Tester writes report.


Step 5 Lead Approval

Lead reviews:

- code
- test report
- architecture compliance

Lead approves or rejects commit.


--------------------------------------------------

# Task Coordination

Tasks are tracked in:

tasks/TASKS.md

Example task:

[ ] Implement task repository

Claimed task:

[ ] Implement task repository @developer

Completed task:

[x] Implement task repository @developer


--------------------------------------------------

# Blocker Tracking

Blocked work must be recorded in:

tasks/BLOCKED.md

Example:

Developer blocked:
Kafka dependency required but not approved by Lead


--------------------------------------------------

# Progress Tracking

Completed work must be recorded in:

tasks/PROGRESS.md


--------------------------------------------------

# Technology Stack

Frameworks:

Axum
Tokio
SQLx
Serde

Database:

PostgreSQL

Testing:

cargo test
integration tests


--------------------------------------------------

# Coding Conventions

Rust code must follow these rules:

- avoid unwrap in production
- use Result for error handling
- follow idiomatic Rust patterns
- use async correctly


Errors must use:

AppError

Defined in:

src/utils/errors.rs


--------------------------------------------------

# API Response Format

All API responses must follow this format:

data: T or null
error: string or null


--------------------------------------------------

# Security Rules

Always validate input.

Validate:

- JSON payloads
- query parameters
- headers

Never log sensitive data.

Passwords must always be hashed.


--------------------------------------------------

# Protected Files

The following files require Lead approval before modification:

Cargo.toml
src/db/migrations
.env


--------------------------------------------------

# Agent Best Practices

Agents must always:

1 read CLAUDE.md
2 read API contracts
3 read TASKS.md
4 check BLOCKED.md
5 follow module boundaries

Agents must never:

- bypass architecture rules
- skip tests
- introduce hidden coupling


--------------------------------------------------

# Final Rule

Architecture correctness is more important than speed.

If an agent is unsure about a change,
the agent must request approval instead of guessing.