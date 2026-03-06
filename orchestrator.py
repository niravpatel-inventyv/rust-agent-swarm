import sys
import os
from datetime import datetime

# Add agents directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents"))

from architect import architect_plan, revise_plan
from lead import lead_review_architecture, lead_review_code
from developer import implement_task, get_unclaimed_tasks, refactor_code
from tester import generate_tests


MAX_ARCHITECTURE_RETRIES = 3
MAX_CODE_REVIEW_RETRIES = 3


def read_file_safe(path, default=""):
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return default


def run():
    """Main orchestration with retry loops:
    
    Architecture loop:  Architect -> Lead (retry up to MAX if rejected)
    Development:        Developer implements all tasks
    Code review loop:   Lead reviews -> Developer refactors (retry up to MAX if rejected)
    Testing:            Tester validates
    Final review:       Lead approves or rejects
    """

    # Step 0: Read feature request
    feature = read_file_safe("feature_request.txt").strip()
    if not feature:
        print("ERROR: No feature request found in feature_request.txt")
        return

    print(f"Feature: {feature}")
    print("=" * 60)

    pipeline_start = datetime.now()
    print(f"Pipeline started at: {pipeline_start.strftime('%Y-%m-%d %H:%M:%S')}")

    # =========================================================
    # PHASE 1: ARCHITECTURE (with retry loop)
    # =========================================================
    print("\n" + "=" * 60)
    print("PHASE 1: ARCHITECTURE DESIGN")
    print("=" * 60)

    arch_approved = False
    arch_session = 0

    for attempt in range(1, MAX_ARCHITECTURE_RETRIES + 1):
        arch_session += 1

        if attempt == 1:
            # First attempt: fresh architecture
            print(f"\n[ARCH ATTEMPT {attempt}] Architect planning...")
            print("-" * 40)
            plan = architect_plan(feature)
            print("Architect: Initial plan created\n")
        else:
            # Revision: architect reads rejection and revises
            print(f"\n[ARCH ATTEMPT {attempt}] Architect revising based on feedback...")
            print("-" * 40)
            plan = revise_plan(feature, rejection_feedback, arch_session)
            print(f"Architect: Revision {arch_session} complete\n")

        # Lead reviews architecture
        print(f"\n[ARCH REVIEW {arch_session}] Lead reviewing architecture...")
        print("-" * 40)
        decision, is_approved = lead_review_architecture(arch_session)

        if is_approved:
            arch_approved = True
            print(f"\nLead: Architecture APPROVED (session {arch_session})\n")
            break
        else:
            rejection_feedback = decision
            print(f"\nLead: Architecture REJECTED (session {arch_session})")
            if attempt < MAX_ARCHITECTURE_RETRIES:
                print(f"  -> Architect will revise (attempt {attempt + 1}/{MAX_ARCHITECTURE_RETRIES})")
            else:
                print(f"  -> Max retries ({MAX_ARCHITECTURE_RETRIES}) reached")

    if not arch_approved:
        print("\n" + "=" * 60)
        print("ORCHESTRATION FAILED: Architecture not approved after "
              f"{MAX_ARCHITECTURE_RETRIES} attempts")
        print("Check tasks/APPROVALS.md for all review sessions")
        print("=" * 60)
        return

    # =========================================================
    # PHASE 2: DEVELOPMENT
    # =========================================================
    print("\n" + "=" * 60)
    print("PHASE 2: DEVELOPMENT")
    print("=" * 60)

    tasks = get_unclaimed_tasks()
    if not tasks:
        print("Developer: No tasks found to implement")
        return

    print(f"\nDeveloper: {len(tasks)} tasks to implement")
    dev_start = datetime.now()
    for i, task in enumerate(tasks, 1):
        task_start = datetime.now()
        print(f"\n  [{i}/{len(tasks)}] [{task_start.strftime('%H:%M:%S')}] Working on: {task}")
        print("  " + "-" * 36)
        implement_task(task)
        task_end = datetime.now()
        elapsed = (task_end - task_start).total_seconds()
        print(f"  [{task_end.strftime('%H:%M:%S')}] Completed in {elapsed:.1f}s")

    dev_end = datetime.now()
    dev_elapsed = (dev_end - dev_start).total_seconds()
    print(f"\nDeveloper: All tasks implemented in {dev_elapsed:.1f}s\n")

    # =========================================================
    # PHASE 3: TESTING
    # =========================================================
    print("\n" + "=" * 60)
    print("PHASE 3: TESTING")
    print("=" * 60)

    print("\n[TESTING] Tester validating...")
    print("-" * 40)
    test_report = generate_tests()
    print("Tester: Done\n")

    # =========================================================
    # PHASE 4: CODE REVIEW (with retry loop)
    # =========================================================
    print("\n" + "=" * 60)
    print("PHASE 4: CODE REVIEW")
    print("=" * 60)

    code_approved = False
    code_session = arch_session  # Continue session numbering

    for attempt in range(1, MAX_CODE_REVIEW_RETRIES + 1):
        code_session += 1

        print(f"\n[CODE REVIEW {code_session}] Lead reviewing code (attempt {attempt})...")
        print("-" * 40)
        decision, is_approved, refactor_feedback = lead_review_code(code_session)

        if is_approved:
            code_approved = True
            print(f"\nLead: Code APPROVED (session {code_session})\n")
            break
        else:
            print(f"\nLead: Code REJECTED (session {code_session})")

            if attempt < MAX_CODE_REVIEW_RETRIES:
                # Developer refactors based on feedback
                print(f"\n[REFACTOR {code_session}] Developer refactoring based on feedback...")
                print("-" * 40)
                refactor_success = refactor_code(refactor_feedback, code_session)

                if refactor_success:
                    # Re-run tests after refactor
                    print(f"\n[RE-TEST {code_session}] Tester re-validating after refactor...")
                    print("-" * 40)
                    test_report = generate_tests()
                    print("Tester: Re-test done\n")
                else:
                    print("  -> Developer refactor failed, will try review again anyway")
            else:
                print(f"  -> Max code review retries ({MAX_CODE_REVIEW_RETRIES}) reached")

    # =========================================================
    # SUMMARY
    # =========================================================
    print("\n" + "=" * 60)
    print("ORCHESTRATION COMPLETE")
    print("=" * 60)

    print(f"\nArchitecture reviews: {arch_session} session(s) — {'APPROVED' if arch_approved else 'REJECTED'}")
    print(f"Code reviews: {code_session - arch_session} session(s) — {'APPROVED' if code_approved else 'REJECTED'}")

    if code_approved:
        print("\nResult: ALL APPROVED — Ready for commit")
    elif arch_approved and not code_approved:
        print("\nResult: Architecture approved but code rejected")
        print("  Manual intervention needed for code quality")
    else:
        print("\nResult: REJECTED — Check approval log")

    print("\nFiles:")
    print("  contracts/api-spec.md  - Architecture spec")
    print("  tasks/TASKS.md         - Task status")
    print("  tasks/APPROVALS.md     - All review sessions")
    print("  tasks/PROGRESS.md      - Development progress")
    print("  reports/test-report.md - Test results")

    pipeline_end = datetime.now()
    total_elapsed = (pipeline_end - pipeline_start).total_seconds()
    print(f"\nTotal pipeline time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    print(f"Started: {pipeline_start.strftime('%H:%M:%S')} | Ended: {pipeline_end.strftime('%H:%M:%S')}")


if __name__ == "__main__":
    run()