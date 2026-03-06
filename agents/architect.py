import ollama


def architect_plan(feature_request):

    claude_rules = open("CLAUDE.md").read()

    prompt = f"""
You are the SENIOR SYSTEM ARCHITECT.

Your job is to design architecture and define tasks.

Project rules:
{claude_rules}

Feature request:
{feature_request}

You must produce:

1 API specification
2 Architecture summary
3 Development task list

Follow modular monolith architecture.

Do NOT implement code.
"""

    response = ollama.chat(
        model="llama3:8b",
        messages=[{"role": "user", "content": prompt}],
    )

    return response["message"]["content"]



import time
import ollama


def run_architect():

    while True:

        try:
            feature = open("feature_request.txt").read()
        except:
            time.sleep(10)
            continue

        claude_rules = open("CLAUDE.md").read()

        prompt = f"""
You are the SENIOR SYSTEM ARCHITECT.

Your job is to design architecture and define tasks.

Project rules:
{claude_rules}

Feature request:
{feature}

You must produce:

1 API specification
2 Architecture summary
3 Development task list

Follow modular monolith architecture.

Do NOT implement code.
"""

        response = ollama.chat(
            model="llama3:8b",
            messages=[{"role": "user", "content": prompt}],
        )

        result = response["message"]["content"]

        open("contracts/api-spec.md", "w").write(result)

        print("Architect updated plan")

        time.sleep(30)


run_architect()