from architect import architect_plan
from lead import lead_review
from developer import implement_task
from tester import generate_tests


def run():

    feature = "Build task CRUD API"

    print("Architect planning...")
    plan = architect_plan(feature)

    with open("contracts/api-spec.md", "w") as f:
        f.write(plan)

    print("Lead reviewing...")
    decision = lead_review()

    if "REJECTED" in decision:
        print("Lead rejected architecture")
        return

    print("Developer implementing...")

    task = "Implement task repository"

    code = implement_task(task)

    with open("src/task_repo.rs", "w") as f:
        f.write(code)

    print("Tester validating...")

    tests = generate_tests()

    with open("reports/test-report.md", "w") as f:
        f.write(tests)

    print("Lead final approval...")

    decision = lead_review()

    print(decision)


if __name__ == "__main__":
    run()