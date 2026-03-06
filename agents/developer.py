import ollama
import subprocess
import os
import time


def run_command(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr


def write_file(path, content):

    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w") as f:
        f.write(content)


def run_developer():

    while True:

        tasks = open("tasks/TASKS.md").read()

        if "[ ]" not in tasks:
            time.sleep(10)
            continue

        task = tasks.split("[ ]")[1].split("\n")[0].strip()

        rules = open("CLAUDE.md").read()
        spec = open("contracts/api-spec.md").read()

        prompt = f"""
You are a senior Rust backend developer.

Project rules:
{rules}

API specification:
{spec}

Your task:
{task}

You can create files and directories.

Follow Rust modular monolith structure.

If a new module is required create:

src/modules/<module_name>/

Files inside module:

mod.rs
model.rs
service.rs
handlers.rs

Output format:

FILE: path
CODE:
<rust code>

Repeat for every file you need to create.
"""

        response = ollama.chat(
            model="deepseek-coder:6.7b",
            messages=[{"role": "user", "content": prompt}],
        )

        result = response["message"]["content"]

        blocks = result.split("FILE:")

        for block in blocks[1:]:

            path = block.split("\n")[0].strip()

            code = block.split("CODE:")[1]

            write_file(path, code)

        print("Developer created files")

        build = run_command("cargo build")

        print(build)

        open("tasks/PROGRESS.md", "a").write(
            f"\nDeveloper completed: {task}\n"
        )

        time.sleep(20)


run_developer()


def self_heal():

    try:
        report = open("reports/test-report.md").read()
    except:
        return

    if "FAILED" not in report:
        return

    rules = open("CLAUDE.md").read()

    prompt = f"""
Tests failed in the Rust project.

Test report:
{report}

Project rules:
{rules}

Fix the code so tests pass.

Return modified Rust code.
"""

    response = ollama.chat(
        model="deepseek-coder:6.7b",
        messages=[{"role": "user", "content": prompt}],
    )

    fix = response["message"]["content"]

    open("src/fix.rs", "w").write(fix)

    subprocess.run(["cargo", "build"])