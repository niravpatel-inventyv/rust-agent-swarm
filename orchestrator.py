import sys
import os

# Add agents directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents"))

from architect import architect_plan
from lead import lead_review
from developer import implement_task, get_unclaimed_tasks
from tester import generate_tests


def read_file_safe(path, default=""):
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return default


def run():
    """Main orchestration: Architect -> Lead -> Developer -> Tester -> Lead"""

    # Step 1: Read feature request
    feature = read_file_safe("feature_request.txt").strip()
    if not feature:
        print("ERROR: No feature request found in feature_request.txt")
        return

    print(f"Feature: {feature}")
    print("=" * 60)

    # Step 2: Architect designs architecture and creates tasks
    print("\n[STEP 1] Architect planning...")
    print("-" * 40)
    plan = architect_plan(feature)
    print("Architect: Done\n")

    # Step 3: Lead reviews architecture
    print("\n[STEP 2] Lead reviewing architecture...")
    print("-" * 40)
    decision = lead_review()

    if "REJECTED" in decision.upper():
        print("\nLead: REJECTED the architecture")
        print("Stopping orchestration. Check tasks/APPROVALS.md for details.")
        return

    print("Lead: Architecture APPROVED\n")

    # Step 4: Developer implements each unclaimed task
    print("\n[STEP 3] Developer implementing tasks...")
    print("-" * 40)
    tasks = get_unclaimed_tasks()

    if not tasks:
        print("Developer: No tasks found to implement")
        return

    for i, task in enumerate(tasks, 1):
        print(f"\n  [{i}/{len(tasks)}] Working on: {task}")
        implement_task(task)

    print("\nDeveloper: All tasks implemented\n")

    # Step 5: Tester validates implementation
    print("\n[STEP 4] Tester validating...")
    print("-" * 40)
    test_report = generate_tests()
    print("Tester: Done\n")

    # Step 6: Lead final review
    print("\n[STEP 5] Lead final review...")
    print("-" * 40)
    final_decision = lead_review()

    # Summary
    print("\n" + "=" * 60)
    print("ORCHESTRATION COMPLETE")
    print("=" * 60)

    if "REJECTED" in final_decision.upper():
        print("Result: Lead REJECTED final implementation")
    else:
        print("Result: Lead APPROVED final implementation")

    print("\nCheck these files for details:")
    print("  contracts/api-spec.md  - Architecture spec")
    print("  tasks/TASKS.md         - Task status")
    print("  tasks/APPROVALS.md     - Approval decisions")
    print("  tasks/PROGRESS.md      - Development progress")
    print("  reports/test-report.md - Test results")


if __name__ == "__main__":
    run()