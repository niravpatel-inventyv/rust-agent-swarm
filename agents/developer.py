import ollama
import subprocess
import os
import re
import time
from datetime import datetime


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


ALLOWED_EXTENSIONS = (".rs", ".toml")


def _is_valid_path(path):
    """Check if path looks like a valid project file."""
    return path and any(path.endswith(ext) for ext in ALLOWED_EXTENSIONS)


def _clean_code_fences(code):
    """Remove markdown code fence markers from code."""
    code = re.sub(r'^```\w*\s*$', '', code, flags=re.MULTILINE)
    return code.strip()


def _extract_path(text):
    """Try to extract a file path from a line of text."""
    # Remove markdown formatting
    cleaned = re.sub(r'[*#`]', '', text).strip()
    # Look for path pattern
    match = re.search(r'((?:src/)?[a-zA-Z0-9_/\-]+\.(?:rs|toml))', cleaned)
    return match.group(1) if match else None


def parse_file_blocks(llm_output):
    """Parse file blocks from LLM output using multiple strategies."""
    files = {}

    # Strategy 1: FILE: path / CODE: format (original expected format)
    if "FILE:" in llm_output:
        parts = re.split(r'(?:^|\n)FILE:\s*', llm_output)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            lines = part.split("\n")
            if not lines:
                continue
            path = lines[0].strip().strip('`').strip('"').strip("'").strip()
            if not _is_valid_path(path):
                continue
            code_start = 1
            for i in range(1, len(lines)):
                line = lines[i].strip()
                if line.startswith("CODE:"):
                    code_start = i + 1
                    break
                if line.startswith("```"):
                    code_start = i + 1
                    break
            code = "\n".join(lines[code_start:])
            code = _clean_code_fences(code)
            if path and code:
                files[path.lstrip("./")] = code

    if files:
        return files

    # Strategy 2: Markdown headers with code fences
    # Matches: ### src/tasks/model.rs  OR  **src/tasks/model.rs**  OR  `src/tasks/model.rs`
    # followed by a ```rust code block
    segments = re.split(r'\n(?=#{1,4}\s|\*\*[a-zA-Z])', llm_output)
    for segment in segments:
        first_line = segment.split("\n")[0]
        path = _extract_path(first_line)
        if not path or not _is_valid_path(path):
            continue
        code_match = re.search(r'```\w*\s*\n(.*?)```', segment, re.DOTALL)
        if code_match:
            code = code_match.group(1).strip()
            if code:
                files[path.lstrip("./")] = code

    if files:
        return files

    # Strategy 3: Code fences with file path as first comment line
    # Matches: ```rust\n// src/tasks/model.rs\n...```
    blocks = re.findall(r'```(?:rust|toml)?\s*\n(.*?)```', llm_output, re.DOTALL)
    for block in blocks:
        lines = block.strip().split("\n")
        if not lines:
            continue
        first = lines[0].strip()
        if first.startswith("//") or first.startswith("#"):
            path = _extract_path(first)
            if path and _is_valid_path(path):
                code = "\n".join(lines[1:]).strip()
                if code:
                    files[path.lstrip("./")] = code

    if files:
        return files

    # Strategy 4: Multiple code fences — try to infer filenames from content
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # Try to infer from mod declarations or struct names
        if "pub mod " in block and len(block.split("\n")) < 10:
            files["src/lib.rs"] = block
        elif "fn main" in block:
            files["src/main.rs"] = block
        elif "[dependencies]" in block or "[package]" in block:
            files["Cargo.toml"] = block

    return files


# Common crate names mapped to Cargo.toml dependency lines
COMMON_DEPS = {
    "axum": 'axum = "0.7"',
    "tokio": 'tokio = { version = "1", features = ["full"] }',
    "serde": 'serde = { version = "1", features = ["derive"] }',
    "serde_json": 'serde_json = "1"',
    "uuid": 'uuid = { version = "1", features = ["v4", "serde"] }',
    "tower": 'tower = "0.5"',
    "tower_http": 'tower-http = { version = "0.6", features = ["cors", "trace"] }',
    "tracing": 'tracing = "0.1"',
    "tracing_subscriber": 'tracing-subscriber = "0.3"',
}


def ensure_dependencies(created_files):
    """Scan created .rs files for crate usage and auto-add missing deps to Cargo.toml."""
    all_code = ""
    for path in created_files:
        if path.endswith(".rs"):
            all_code += read_file_safe(path) + "\n"

    cargo = read_file_safe("Cargo.toml")
    needed = []
    for crate_name, dep_line in COMMON_DEPS.items():
        cargo_name = crate_name.replace("_", "-")
        if re.search(rf'use\s+{crate_name}', all_code) and cargo_name not in cargo:
            needed.append(dep_line)

    if needed:
        lines = cargo.rstrip().split("\n")
        # Find [dependencies] line and insert after it
        dep_idx = None
        for i, line in enumerate(lines):
            if line.strip() == "[dependencies]":
                dep_idx = i
                break
        if dep_idx is not None:
            for dep in reversed(needed):
                lines.insert(dep_idx + 1, dep)
        else:
            lines.append("\n[dependencies]")
            lines.extend(needed)
        with open("Cargo.toml", "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"Developer: Auto-added {len(needed)} dependencies to Cargo.toml: {[d.split('=')[0].strip() for d in needed]}")


def write_parsed_files(file_blocks):
    """Write parsed file blocks to disk, handling path prefixes correctly."""
    created_files = []
    for path, code in file_blocks.items():
        # Only prepend src/ for .rs files that don't already have it
        if path.endswith(".rs") and not path.startswith("src/"):
            path = "src/" + path
        # Cargo.toml always goes to project root
        if path.endswith("Cargo.toml"):
            path = "Cargo.toml"
        write_file(path, code)
        created_files.append(path)
        print(f"Developer: Created {path}")
    return created_files


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
        f.write("\n" + entry)


def implement_task(task_name):
    """Implement a specific task. Called by orchestrator."""

    task_start = datetime.now()
    print(f"Developer: [START {task_start.strftime('%H:%M:%S')}] Task: {task_name}")

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
2. Create files under src/<module_name>/ with: mod.rs, model.rs, service.rs, repository.rs, handlers.rs
3. Use proper error handling with Result types - NEVER use unwrap() in production code
4. Use async/await with tokio where appropriate
5. Follow the API response format: {{ "data": T, "error": null }} or {{ "data": null, "error": "message" }}
6. Use serde for serialization/deserialization
7. Make sure the code compiles with the existing code
8. If you need to update src/main.rs to declare modules, include that file too

OUTPUT FORMAT - You MUST use this EXACT format for EVERY file:

FILE: src/<module_name>/model.rs
CODE:
use serde::{{Serialize, Deserialize}};

#[derive(Debug, Serialize, Deserialize)]
pub struct Entity {{
    pub id: String,
    pub name: String,
}}

FILE: src/<module_name>/mod.rs
CODE:
pub mod model;
pub mod repository;
pub mod service;
pub mod handlers;

IMPORTANT: Replace <module_name> with the actual module name from the task (e.g. if task says src/users/, use src/users/).
Do NOT hardcode "tasks" as the module name — use whatever module name the task specifies.

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
    created_files = write_parsed_files(file_blocks)

    # Auto-detect and add missing dependencies
    ensure_dependencies(created_files)

    # Try to build
    build_output, exit_code = run_command("cargo build 2>&1")
    print(f"Developer: cargo build exit code: {exit_code}")

    if exit_code != 0:
        print(f"Developer: Build FAILED — logging errors...")
        print(f"Developer: Build errors:\n{build_output[:2000]}")
        print(f"Developer: Attempting self-heal (sending errors to LLM)...")
        fixed = self_heal(task_name, build_output, created_files)
        if fixed:
            print(f"Developer: Self-heal SUCCEEDED — build now passes")
        else:
            print(f"Developer: Self-heal FAILED — build still broken")
            with open("tasks/BLOCKED.md", "a") as f:
                f.write(f"""
agent: developer
task: {task_name}
problem: cargo build failed after self-heal attempt
attempted_solution: LLM fix attempt did not resolve errors
build_errors: {build_output[:500]}
status: unresolved

""")

    # Mark task ready for testing
    complete_task(task_name)

    # Update progress in the correct format
    update_progress(task_name, created_files)

    task_end = datetime.now()
    elapsed = (task_end - task_start).total_seconds()
    print(f"Developer: [END {task_end.strftime('%H:%M:%S')}] Task: {task_name} — took {elapsed:.1f}s")
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

    fixed_files = write_parsed_files(fix_blocks)

    # Re-check dependencies after fix
    ensure_dependencies(fixed_files + file_paths)

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

    modified_files = write_parsed_files(file_blocks)

    # Re-check dependencies after refactor
    ensure_dependencies(modified_files)

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