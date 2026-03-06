import ollama
import subprocess
import os
import re
import time


def read_file_safe(path, default=""):
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return default


def write_file(path, content):
    """Write content to a file, creating directories as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def run_command(cmd):
    """Run a shell command and return (output, exit_code)."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr, result.returncode


def get_unclaimed_tasks():
    """Find tasks marked [ ] in TASKS.md that are ready for development."""
    tasks_content = read_file_safe("tasks/TASKS.md")
    tasks = []
    for line in tasks_content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("[ ] "):
            task_name = stripped[4:].strip()
            # Skip format documentation lines (contain = or are status descriptions)
            if task_name and "=" not in task_name and "not started" not in task_name.lower():
                tasks.append(task_name)
    return tasks


def claim_task(task_name):
    """Mark task as [DEV] in TASKS.md."""
    content = read_file_safe("tasks/TASKS.md")
    content = content.replace(f"[ ] {task_name}", f"[DEV] {task_name}", 1)
    with open("tasks/TASKS.md", "w") as f:
        f.write(content)


def complete_task(task_name):
    """Mark task as [TEST] in TASKS.md."""
    content = read_file_safe("tasks/TASKS.md")
    content = content.replace(f"[DEV] {task_name}", f"[TEST] {task_name}", 1)
    with open("tasks/TASKS.md", "w") as f:
        f.write(content)


def get_existing_rust_code():
    """Read all existing .rs files for context."""
    code = ""
    for root, dirs, files in os.walk("src"):
        for fname in sorted(files):
            if fname.endswith(".rs"):
                fpath = os.path.join(root, fname)
                content = read_file_safe(fpath)
                code += f"\n--- {fpath} ---\n{content}\n"
    return code


def parse_file_blocks(llm_output):
    """Parse FILE: path / CODE: blocks from LLM output."""
    files = {}

    # Split by FILE: markers
    parts = re.split(r'(?:^|\n)FILE:\s*', llm_output)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        lines = part.split("\n")
        if not lines:
            continue

        # First line is the file path
        path = lines[0].strip().strip('`').strip('"').strip("'").strip()
        if not path or not path.endswith(".rs"):
            continue

        # Find CODE: marker or first code fence
        code_start = 1
        for i in range(1, len(lines)):
            line = lines[i].strip()
            if line.startswith("CODE:"):
                code_start = i + 1
                break
            if line.startswith("```"):
                code_start = i + 1
                break

        # Extract code
        code_lines = lines[code_start:]
        code = "\n".join(code_lines)

        # Remove markdown code fences
        code = re.sub(r'^```\w*\s*\n?', '', code, flags=re.MULTILINE)
        code = re.sub(r'\n?```\s*$', '', code)
        code = code.strip()

        if path and code:
            path = path.lstrip("./")
            files[path] = code

    return files


def update_progress(task_name, files_list):
    """Append progress entry in the correct format from PROGRESS.md."""
    files_str = "\n".join(files_list)
    entry = f"""
agent: developer
task: {task_name}
description: Implemented {task_name}
files_modified:
{files_str}

"""
    with open("tasks/PROGRESS.md", "a") as f:
        f.write(entry)


def implement_task(task_name):
    """Implement a specific task. Called by orchestrator."""

    # Read all context files
    claude_rules = read_file_safe("CLAUDE.md")
    api_spec = read_file_safe("contracts/api-spec.md")
    blocked = read_file_safe("tasks/BLOCKED.md")
    existing_code = get_existing_rust_code()

    # Check if task is blocked
    if task_name in blocked:
        print(f"Developer: Task '{task_name}' appears in BLOCKED.md, skipping")
        return None

    # Claim the task in TASKS.md
    claim_task(task_name)
    print(f"Developer: Claimed task: {task_name}")

    prompt = f"""You are a senior Rust backend developer working on a modular monolith project.

PROJECT RULES (read carefully and follow strictly):
{claude_rules}

API SPECIFICATION:
{api_spec}

EXISTING RUST CODE IN THE PROJECT:
{existing_code}

YOUR TASK: {task_name}

CRITICAL INSTRUCTIONS:
1. Follow the modular monolith structure from CLAUDE.md
2. Create files under src/modules/<module_name>/ with: mod.rs, model.rs, service.rs, repository.rs, handlers.rs
3. Use proper error handling with Result types - NEVER use unwrap() in production code
4. Use async/await with tokio where appropriate
5. Follow the API response format: {{ "data": T, "error": null }} or {{ "data": null, "error": "message" }}
6. Use serde for serialization/deserialization
7. Make sure the code compiles with the existing code
8. If you need to update src/main.rs to declare modules, include that file too

OUTPUT FORMAT - You MUST use this EXACT format for EVERY file:

FILE: src/modules/tasks/model.rs
CODE:
use serde::{{Serialize, Deserialize}};

#[derive(Debug, Serialize, Deserialize)]
pub struct Task {{
    pub id: String,
    pub title: String,
}}

FILE: src/modules/tasks/mod.rs
CODE:
pub mod model;
pub mod repository;
pub mod service;
pub mod handlers;

Generate ALL files needed for this task. Every FILE: block must have COMPLETE, COMPILABLE Rust code.
Do NOT use placeholder comments, todo!(), or unimplemented!().
Do NOT skip any file that is needed.
"""

    response = ollama.chat(
        model="deepseek-coder:6.7b",
        messages=[{"role": "user", "content": prompt}],
    )

    result = response["message"]["content"]

    # Parse file blocks from LLM output
    file_blocks = parse_file_blocks(result)

    if not file_blocks:
        print(f"Developer: WARNING - Could not parse any file blocks from LLM output")
        print(f"Developer: Raw output preview: {result[:500]}")

        # Log blocker in the correct format
        with open("tasks/BLOCKED.md", "a") as f:
            f.write(f"""
agent: developer
task: {task_name}
problem: Could not parse LLM output into file blocks
attempted_solution: Need to re-run with adjusted prompt
status: unresolved

""")
        return result

    # Write all parsed files to disk
    created_files = []
    for path, code in file_blocks.items():
        # Ensure path starts with src/
        if not path.startswith("src/"):
            path = "src/" + path

        write_file(path, code)
        created_files.append(path)
        print(f"Developer: Created {path}")

    # Try to build
    build_output, exit_code = run_command("cargo build 2>&1")
    print(f"Developer: cargo build exit code: {exit_code}")

    if exit_code != 0:
        print(f"Developer: Build failed, attempting self-heal...")
        print(f"Developer: Build errors:\n{build_output[:1000]}")
        fixed = self_heal(task_name, build_output, created_files)
        if not fixed:
            with open("tasks/BLOCKED.md", "a") as f:
                f.write(f"""
agent: developer
task: {task_name}
problem: cargo build failed after self-heal attempt
attempted_solution: LLM fix attempt did not resolve errors
status: unresolved

""")

    # Mark task ready for testing
    complete_task(task_name)

    # Update progress in the correct format
    update_progress(task_name, created_files)

    print(f"Developer: Task '{task_name}' complete, marked [TEST]")
    return result


def self_heal(task_name, build_error, file_paths):
    """Attempt to fix build errors by re-prompting LLM."""

    claude_rules = read_file_safe("CLAUDE.md")

    # Read the files we created
    file_contents = ""
    for path in file_paths:
        content = read_file_safe(path)
        file_contents += f"\n--- {path} ---\n{content}\n"

    prompt = f"""The Rust project failed to compile. Fix ALL errors.

BUILD ERRORS:
{build_error}

CURRENT FILES:
{file_contents}

PROJECT RULES:
{claude_rules}

Fix ALL compilation errors. Return the corrected files in this EXACT format:

FILE: <exact file path>
CODE:
<complete corrected rust code>

Only include files that need changes. Return COMPLETE file contents, not just changed parts.
"""

    response = ollama.chat(
        model="deepseek-coder:6.7b",
        messages=[{"role": "user", "content": prompt}],
    )

    fix_result = response["message"]["content"]
    fix_blocks = parse_file_blocks(fix_result)

    if not fix_blocks:
        print("Developer: Self-heal could not parse fix output")
        return False

    for path, code in fix_blocks.items():
        if not path.startswith("src/"):
            path = "src/" + path
        write_file(path, code)
        print(f"Developer: Fixed {path}")

    # Rebuild
    build_output, exit_code = run_command("cargo build 2>&1")
    print(f"Developer: Rebuild exit code: {exit_code}")

    return exit_code == 0


def refactor_code(refactor_feedback, session_number):
    """Refactor code based on Lead's code review feedback."""

    claude_rules = read_file_safe("CLAUDE.md")
    api_spec = read_file_safe("contracts/api-spec.md")
    existing_code = get_existing_rust_code()

    prompt = f"""You are a senior Rust backend developer. The Lead rejected your code and wants refactoring.

This is REFACTOR SESSION {session_number}. You MUST address ALL of the Lead's feedback.

PROJECT RULES:
{claude_rules}

API SPECIFICATION:
{api_spec}

CURRENT SOURCE CODE:
{existing_code}

LEAD'S REFACTOR INSTRUCTIONS (address ALL points):
{refactor_feedback}

CRITICAL:
1. Read the Lead's feedback carefully
2. Fix EVERY issue mentioned
3. Keep code that was not mentioned as problematic
4. Follow the modular monolith structure
5. Use proper error handling with Result — NEVER use unwrap()
6. Make sure the code compiles

OUTPUT FORMAT — use this EXACT format for EVERY file you modify:

FILE: <exact file path>
CODE:
<complete file content — not just the changed parts>

Return COMPLETE file contents for every file that needs changes.
Do NOT skip any file that needs modification.
"""

    response = ollama.chat(
        model="deepseek-coder:6.7b",
        messages=[{"role": "user", "content": prompt}],
    )

    result = response["message"]["content"]
    file_blocks = parse_file_blocks(result)

    if not file_blocks:
        print(f"Developer: Refactor {session_number} - Could not parse LLM output")
        with open("tasks/BLOCKED.md", "a") as f:
            f.write(f"""
agent: developer
task: Refactor session {session_number}
problem: Could not parse refactor LLM output
attempted_solution: Need manual intervention
status: unresolved

""")
        return False

    modified_files = []
    for path, code in file_blocks.items():
        if not path.startswith("src/"):
            path = "src/" + path
        write_file(path, code)
        modified_files.append(path)
        print(f"Developer: Refactored {path}")

    # Build check
    build_output, exit_code = run_command("cargo build 2>&1")
    print(f"Developer: Refactor build exit code: {exit_code}")

    if exit_code != 0:
        print(f"Developer: Refactor build failed, attempting self-heal...")
        fixed = self_heal(f"Refactor session {session_number}", build_output, modified_files)
        if not fixed:
            with open("tasks/BLOCKED.md", "a") as f:
                f.write(f"""
agent: developer
task: Refactor session {session_number}
problem: cargo build failed after refactor + self-heal
attempted_solution: LLM fix did not resolve errors
status: unresolved

""")
            return False

    # Log progress
    files_str = "\n".join(modified_files)
    with open("tasks/PROGRESS.md", "a") as f:
        f.write(f"""
agent: developer
task: Refactor session {session_number}
description: Refactored code based on Lead feedback
files_modified:
{files_str}

""")

    print(f"Developer: Refactor session {session_number} complete")
    return True


def run_developer():
    """Standalone continuous loop mode."""
    while True:
        # Read BLOCKED.md before starting
        blocked = read_file_safe("tasks/BLOCKED.md")

        tasks = get_unclaimed_tasks()
        if not tasks:
            print("Developer: No unclaimed tasks, waiting...")
            time.sleep(10)
            continue

        # Pick first available task
        task = tasks[0]

        # Skip if blocked
        if task in blocked:
            print(f"Developer: Task '{task}' is blocked, skipping")
            continue

        implement_task(task)
        time.sleep(20)


if __name__ == "__main__":
    run_developer()