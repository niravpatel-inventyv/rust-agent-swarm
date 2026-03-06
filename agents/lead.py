import ollama
import time


def read_file_safe(path, default=""):
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return default


def lead_review():
    """Review architecture and tasks, write approvals in the correct format."""

    claude_rules = read_file_safe("CLAUDE.md")
    tasks = read_file_safe("tasks/TASKS.md")
    spec = read_file_safe("contracts/api-spec.md")
    progress = read_file_safe("tasks/PROGRESS.md")
    test_report = read_file_safe("reports/test-report.md")
    approvals = read_file_safe("tasks/APPROVALS.md")
    blocked = read_file_safe("tasks/BLOCKED.md")

    prompt = f"""You are the LEAD ENGINEER responsible for governance and approvals.

PROJECT RULES (read carefully):
{claude_rules}

ARCHITECTURE SPECIFICATION:
{spec}

CURRENT TASK LIST:
{tasks}

DEVELOPMENT PROGRESS:
{progress}

TEST REPORT:
{test_report}

BLOCKED ITEMS:
{blocked}

EXISTING APPROVALS FILE (read the format carefully):
{approvals}

YOUR RESPONSIBILITIES:
1. Review the architecture specification for correctness
2. Review each task in the task list
3. Check that modular monolith boundaries are respected
4. Verify tasks follow the project rules
5. Approve or reject each pending item

You MUST write your approvals in this EXACT format. One block per item:

request_by: architect
type: architecture
description: <what is being approved or rejected>
decision: approved
approved_by: lead

For rejections, add a reason field:

request_by: architect
type: architecture
description: <what is being rejected>
decision: rejected
approved_by: lead
reason: <why it was rejected>

Separate each approval block with a blank line.

At the very end of your response, write one of these on its own line:
APPROVED
or
REJECTED

This indicates your overall decision on the current architecture/implementation.
"""

    response = ollama.chat(
        model="llama3:8b",
        messages=[{"role": "user", "content": prompt}],
    )

    decision = response["message"]["content"]

    # Append to APPROVALS.md (never overwrite - preserve history)
    with open("tasks/APPROVALS.md", "a") as f:
        f.write("\n\n--------------------------------------------------\n\n")
        f.write("# REVIEW SESSION\n\n")
        f.write(decision)
        f.write("\n")

    print("Lead: Decision recorded in tasks/APPROVALS.md")
    return decision


def run_lead():
    """Standalone continuous loop mode."""
    while True:
        lead_review()
        time.sleep(30)


if __name__ == "__main__":
    run_lead()