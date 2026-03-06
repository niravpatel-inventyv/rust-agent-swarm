
import time
import ollama


def run_lead():

    while True:

        claude_rules = open("CLAUDE.md").read()
        tasks = open("tasks/TASKS.md").read()
        spec = open("contracts/api-spec.md").read()

        prompt = f"""
You are the LEAD ENGINEER.

Your job is governance and approval.

Project rules:
{claude_rules}

Architecture spec:
{spec}

Task list:
{tasks}

Review tasks and architecture.

You must decide:

APPROVED
or
REJECTED

Explain reasoning.
"""

        response = ollama.chat(
            model="llama3:8b",
            messages=[{"role": "user", "content": prompt}],
        )

        decision = response["message"]["content"]

        open("tasks/APPROVALS.md", "w").write(decision)

        print("Lead decision updated")

        time.sleep(30)


run_lead()