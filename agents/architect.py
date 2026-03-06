import ollama
import os
import re
import time


def read_file_safe(path, default=""):
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return default


def architect_plan(feature_request):
    """Design architecture, generate API spec, and create task list."""

    claude_rules = read_file_safe("CLAUDE.md")
    existing_tasks = read_file_safe("tasks/TASKS.md")

    prompt = f"""You are the SENIOR SYSTEM ARCHITECT for a Rust modular monolith backend project.

PROJECT RULES (read carefully):
{claude_rules}

FEATURE REQUEST:
{feature_request}

EXISTING TASK FILE FORMAT (you MUST follow this exact format):
{existing_tasks}

You must produce TWO clearly separated outputs.

SECTION 1 - API SPECIFICATION:
Write a detailed REST API specification. For each endpoint include:
- Method (GET/POST/PUT/DELETE)
- Path
- Request body (JSON example)
- Response body (JSON example using format: {{"data": T, "error": null}})
- Error responses

SECTION 2 - TASK LIST:
Write development tasks, one per line, using EXACTLY this format:

TASKS:
[ ] Create task domain model in src/modules/tasks/model.rs
[ ] Implement task repository in src/modules/tasks/repository.rs
[ ] Implement task service layer in src/modules/tasks/service.rs
[ ] Create HTTP handlers in src/modules/tasks/handlers.rs
[ ] Create module declaration in src/modules/tasks/mod.rs
[ ] Wire task module routes into src/main.rs
[ ] Add integration tests for task API

RULES:
- Follow modular monolith architecture from CLAUDE.md
- Each module needs: mod.rs, model.rs, service.rs, repository.rs, handlers.rs
- All modules go under src/modules/
- Do NOT write any implementation code
- Order tasks by dependency (foundational tasks first)
- Start each task line with [ ] exactly
"""

    response = ollama.chat(
        model="llama3:8b",
        messages=[{"role": "user", "content": prompt}],
    )

    result = response["message"]["content"]

    # Write full plan to api-spec.md
    with open("contracts/api-spec.md", "w") as f:
        f.write(result)

    # Extract task lines and update TASKS.md
    task_lines = []
    for line in result.split("\n"):
        stripped = line.strip()
        # Match lines starting with [ ] or - [ ] or * [ ]
        if re.match(r'^[-*]?\s*\[ \]\s+\S', stripped):
            task = re.sub(r'^[-*]\s*', '', stripped)
            task_lines.append(task)

    if task_lines:
        _update_tasks_file(task_lines)
        print(f"Architect: Created {len(task_lines)} tasks in tasks/TASKS.md")
    else:
        print("Architect: WARNING - Could not extract tasks from LLM output")
        print("Architect: Will write raw task section to TASKS.md")
        # Fallback: try to find any task-like lines
        for line in result.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and len(stripped) > 10:
                if any(kw in stripped.lower() for kw in ["implement", "create", "add", "build", "design", "write"]):
                    task_lines.append(f"[ ] {stripped}")
        if task_lines:
            _update_tasks_file(task_lines)

    print("Architect: Updated contracts/api-spec.md")
    return result


def _update_tasks_file(task_lines):
    """Rewrite TASKS.md with standard header format and new tasks."""

    header = """# TASK BOARD

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

"""

    footer = """

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
"""

    # Preserve any existing in-progress or completed tasks
    existing = read_file_safe("tasks/TASKS.md")
    preserved = []
    for line in existing.split("\n"):
        stripped = line.strip()
        if stripped.startswith("[DEV]") or stripped.startswith("[TEST]") or stripped.startswith("[DONE]"):
            preserved.append(stripped)

    all_tasks = preserved + task_lines
    content = header + "\n".join(all_tasks) + "\n" + footer

    with open("tasks/TASKS.md", "w") as f:
        f.write(content)


def run_architect():
    """Standalone continuous loop mode."""
    while True:
        feature = read_file_safe("feature_request.txt").strip()
        if not feature:
            print("Architect: No feature request found, waiting...")
            time.sleep(10)
            continue

        architect_plan(feature)
        time.sleep(30)


if __name__ == "__main__":
    run_architect()