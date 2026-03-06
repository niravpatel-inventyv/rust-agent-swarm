import ollama
import subprocess
import time


def run_tester():

    while True:

        progress = open("tasks/PROGRESS.md").read()
        spec = open("contracts/api-spec.md").read()
        claude_rules = open("CLAUDE.md").read()
        

        prompt = f"""
You are the QA ENGINEER.

Project rules:
{claude_rules}

API specification:
{spec}

Development progress:
{progress}

Write Rust unit and integration tests.

Tests must cover:

- success scenarios
- invalid input
- concurrency
- edge cases

Output format:

TEST_REPORT
UNIT_TESTS
INTEGRATION_TESTS
"""

        response = ollama.chat(
            model="deepseek-coder:6.7b",
            messages=[{"role": "user", "content": prompt}],
        )

        tests = response["message"]["content"]

        open("tests/generated_tests.rs", "w").write(tests)

        subprocess.run(["cargo", "test"])

        open("reports/test-report.md", "w").write("tests executed")

        print("Tester ran tests")

        time.sleep(30)


run_tester()