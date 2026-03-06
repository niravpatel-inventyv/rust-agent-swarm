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
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def run_command(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr, result.returncode


def get_source_code():
    """Read all Rust source files for context."""
    code = ""
    for root, dirs, files in os.walk("src"):
        for fname in sorted(files):
            if fname.endswith(".rs"):
                fpath = os.path.join(root, fname)
                content = read_file_safe(fpath)
                code += f"\n--- {fpath} ---\n{content}\n"
    return code


def extract_test_code(llm_output):
    """Extract valid Rust test code from LLM output."""

    # Try to find ```rust code blocks first
    code_blocks = re.findall(r'```rust\s*\n(.*?)```', llm_output, re.DOTALL)
    if code_blocks:
        return "\n\n".join(code_blocks)

    # Try generic code blocks
    code_blocks = re.findall(r'```\s*\n(.*?)```', llm_output, re.DOTALL)
    if code_blocks:
        return "\n\n".join(code_blocks)

    # Fallback: try to extract lines that look like Rust code
    lines = llm_output.split("\n")
    rust_lines = []
    in_code = False
    for line in lines:
        stripped = line.strip()
        if any(stripped.startswith(kw) for kw in ["use ", "#[", "fn ", "mod ", "pub ", "struct ", "impl ", "async "]):
            in_code = True
        if in_code:
            rust_lines.append(line)

    if rust_lines:
        return "\n".join(rust_lines)

    # Last resort: return raw output (will likely fail to compile, but at least it's in the file)
    return llm_output


def generate_tests():
    """Generate and run tests. Called by orchestrator."""

    claude_rules = read_file_safe("CLAUDE.md")
    api_spec = read_file_safe("contracts/api-spec.md")
    progress = read_file_safe("tasks/PROGRESS.md")
    source_code = get_source_code()

    # Check if there's actual implementation code to test
    has_real_code = False
    for root, dirs, files in os.walk("src"):
        for fname in files:
            if fname.endswith(".rs") and fname != "main.rs":
                has_real_code = True
                break

    if not has_real_code:
        main_content = read_file_safe("src/main.rs")
        if main_content.strip() == 'fn main() {\n    println!("Hello, world!");\n}'.strip():
            print("Tester: No implementation code found in src/, skipping tests")
            report = """# Test Report

status: SKIPPED
reason: No implementation code found in src/
tests_run: 0
tests_passed: 0
tests_failed: 0
"""
            with open("reports/test-report.md", "w") as f:
                f.write(report)
            return report

    prompt = f"""You are a QA engineer writing Rust tests for a modular monolith backend project.

PROJECT RULES (read carefully):
{claude_rules}

API SPECIFICATION:
{api_spec}

DEVELOPMENT PROGRESS:
{progress}

SOURCE CODE TO TEST:
{source_code}

Write comprehensive Rust tests. You must cover:
1. Unit tests for models and data structures
2. Unit tests for service layer logic
3. Tests for error handling (invalid input, missing data)
4. Edge cases (empty strings, boundary values, zero/negative numbers)

REQUIREMENTS:
- Output ONLY valid, compilable Rust code
- Use #[cfg(test)] module for unit tests
- Use #[test] attribute for each test function
- Use assert!, assert_eq!, assert_ne! macros
- Test both success AND failure cases
- Do NOT use unwrap() carelessly - prefer assert patterns
- Make sure imports match the actual module structure in the source code

OUTPUT FORMAT:
Wrap ALL test code in a single ```rust code block.

Example structure:

```rust
#[cfg(test)]
mod tests {{
    use super::*;

    #[test]
    fn test_create_task() {{
        // test code
    }}

    #[test]
    fn test_invalid_input() {{
        // test code
    }}
}}
```

Generate at least 5 test functions covering different scenarios.
"""

    response = ollama.chat(
        model="deepseek-coder:6.7b",
        messages=[{"role": "user", "content": prompt}],
    )

    result = response["message"]["content"]

    # Extract actual Rust test code from LLM output
    test_code = extract_test_code(result)

    # Write test file
    write_file("tests/generated_tests.rs", test_code)
    print("Tester: Wrote tests to tests/generated_tests.rs")

    # Run tests
    test_output, exit_code = run_command("cargo test 2>&1")
    print(f"Tester: cargo test exit code: {exit_code}")

    # Parse test results
    passed = len(re.findall(r'test .+ \.\.\. ok', test_output))
    failed = len(re.findall(r'test .+ \.\.\. FAILED', test_output))

    status = "PASSED" if exit_code == 0 else "FAILED"

    # Write test report in the correct format from reports/test-report.md
    report = f"""# Test Report

status: {status}
tests_run: {passed + failed}
tests_passed: {passed}
tests_failed: {failed}

## Test Output

{test_output}

## Files Tested

{source_code[:1000]}
"""

    with open("reports/test-report.md", "w") as f:
        f.write(report)

    # If tests pass, update TASKS.md - mark [TEST] tasks as [DONE]
    if exit_code == 0:
        tasks_content = read_file_safe("tasks/TASKS.md")
        updated = tasks_content.replace("[TEST]", "[DONE]")
        with open("tasks/TASKS.md", "w") as f:
            f.write(updated)
        print("Tester: All [TEST] tasks marked as [DONE]")

    print(f"Tester: Report written to reports/test-report.md ({status})")
    return report


def run_tester():
    """Standalone continuous loop mode."""
    while True:
        progress = read_file_safe("tasks/PROGRESS.md")
        if "developer" not in progress.lower():
            print("Tester: No developer progress yet, waiting...")
            time.sleep(10)
            continue

        generate_tests()
        time.sleep(30)


if __name__ == "__main__":
    run_tester()