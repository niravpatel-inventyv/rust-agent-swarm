import ollama
import os
import time


def read_file_safe(path, default=""):
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return default


def _get_session_number():
    """Count existing review sessions in APPROVALS.md to determine next number."""
    approvals = read_file_safe("tasks/APPROVALS.md")
    count = approvals.count("# REVIEW SESSION")
    return count + 1


def lead_review_architecture(session_number=None):
    """Review architecture spec. Returns (decision_text, is_approved)."""

    if session_number is None:
        session_number = _get_session_number()

    claude_rules = read_file_safe("CLAUDE.md")
    tasks = read_file_safe("tasks/TASKS.md")
    spec = read_file_safe("contracts/api-spec.md")
    approvals = read_file_safe("tasks/APPROVALS.md")

    prompt = f"""You are the LEAD ENGINEER responsible for governance and approvals.

This is ARCHITECTURE REVIEW SESSION {session_number}.

PROJECT RULES (read carefully):
{claude_rules}

ARCHITECTURE SPECIFICATION TO REVIEW:
{spec}

CURRENT TASK LIST:
{tasks}

EXISTING APPROVALS (review history):
{approvals}

YOUR RESPONSIBILITIES:
1. Review the architecture specification for correctness
2. Check that modular monolith boundaries are respected
3. Verify the API specification follows project rules
4. Review each task for clarity and completeness
5. Ensure tasks follow the correct module structure: src/<name>/

You MUST write your review in this EXACT format:

request_by: architect
type: architecture
description: <what you reviewed>
decision: approved OR rejected
approved_by: lead
reason: <detailed explanation of why approved or rejected>

If REJECTED, you MUST explain exactly what needs to change so the Architect can fix it.

At the very end of your response, write one of these on its own line:
APPROVED
or
REJECTED
"""

    response = ollama.chat(
        model="llama3:8b",
        messages=[{"role": "user", "content": prompt}],
    )

    decision = response["message"]["content"]

    # Append to APPROVALS.md with session number
    with open("tasks/APPROVALS.md", "a") as f:
        f.write(f"\n\n--------------------------------------------------\n\n")
        f.write(f"# REVIEW SESSION {session_number} — ARCHITECTURE REVIEW\n\n")
        f.write(decision)
        f.write("\n")

    is_approved = "REJECTED" not in decision.upper()
    status = "APPROVED" if is_approved else "REJECTED"
    print(f"Lead: Architecture Review Session {session_number}: {status}")
    return decision, is_approved


def lead_review_code(session_number=None):
    """Review developer implementation. Returns (decision_text, is_approved, refactor_feedback)."""

    if session_number is None:
        session_number = _get_session_number()

    claude_rules = read_file_safe("CLAUDE.md")
    tasks = read_file_safe("tasks/TASKS.md")
    spec = read_file_safe("contracts/api-spec.md")
    progress = read_file_safe("tasks/PROGRESS.md")
    test_report = read_file_safe("reports/test-report.md")
    approvals = read_file_safe("tasks/APPROVALS.md")
    blocked = read_file_safe("tasks/BLOCKED.md")

    # Read all source code
    source_code = ""
    for root, dirs, files in os.walk("src"):
        for fname in sorted(files):
            if fname.endswith(".rs"):
                fpath = os.path.join(root, fname)
                content = read_file_safe(fpath)
                source_code += f"\n--- {fpath} ---\n{content}\n"

    prompt = f"""You are the LEAD ENGINEER doing a CODE REVIEW.

This is CODE REVIEW SESSION {session_number}.

PROJECT RULES (read carefully):
{claude_rules}

ARCHITECTURE SPECIFICATION:
{spec}

SOURCE CODE TO REVIEW:
{source_code}

TASK STATUS:
{tasks}

DEVELOPMENT PROGRESS:
{progress}

TEST REPORT:
{test_report}

BLOCKED ITEMS:
{blocked}

REVIEW HISTORY:
{approvals}

YOUR RESPONSIBILITIES:
1. Review ALL source code for correctness and quality
2. Check that modular monolith boundaries are respected
3. Verify error handling uses Result types, no unwrap() in production
4. Check that API response format is correct: {{"data": T, "error": null}}
5. Verify the code matches the architecture specification
6. Check for security issues (input validation, no sensitive data logging)

You MUST write your review in this EXACT format:

request_by: developer
type: code-review
description: <what you reviewed>
decision: approved OR rejected
approved_by: lead

If REJECTED, you MUST provide specific refactoring instructions:

REFACTOR_INSTRUCTIONS:
- <specific file and what needs to change>
- <specific file and what needs to change>
- <etc>

Be specific about file paths and what code needs to change.

At the very end of your response, write one of these on its own line:
APPROVED
or
REJECTED
"""

    response = ollama.chat(
        model="llama3:8b",
        messages=[{"role": "user", "content": prompt}],
    )

    decision = response["message"]["content"]

    # Append to APPROVALS.md with session number
    with open("tasks/APPROVALS.md", "a") as f:
        f.write(f"\n\n--------------------------------------------------\n\n")
        f.write(f"# REVIEW SESSION {session_number} — CODE REVIEW\n\n")
        f.write(decision)
        f.write("\n")

    is_approved = "REJECTED" not in decision.upper()
    status = "APPROVED" if is_approved else "REJECTED"
    print(f"Lead: Code Review Session {session_number}: {status}")

    # Extract refactor instructions if rejected
    refactor_feedback = ""
    if not is_approved:
        if "REFACTOR_INSTRUCTIONS:" in decision:
            refactor_feedback = decision.split("REFACTOR_INSTRUCTIONS:")[1]
            # Cut off at APPROVED/REJECTED line
            for marker in ["APPROVED", "REJECTED"]:
                if marker in refactor_feedback:
                    refactor_feedback = refactor_feedback.split(marker)[0]
            refactor_feedback = refactor_feedback.strip()
        else:
            # Use the whole decision as feedback
            refactor_feedback = decision

    return decision, is_approved, refactor_feedback


def lead_review():
    """Legacy function for backward compatibility. Does architecture review."""
    decision, _ = lead_review_architecture()
    return decision


def run_lead():
    """Standalone continuous loop mode."""
    while True:
        lead_review()
        time.sleep(30)


if __name__ == "__main__":
    run_lead()