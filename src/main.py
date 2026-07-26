import os
import json
import time
from pathlib import Path

from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"
REAL_SCHEMA = BASE_DIR / "schemas" / "budget_input_schema.json"
EXAMPLE_SCHEMA = BASE_DIR / "schemas" / "budget_input_schema.example.json"
SCHEMA_FILE = REAL_SCHEMA if REAL_SCHEMA.exists() else EXAMPLE_SCHEMA
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLARIFIER_MODEL = os.getenv("CLARIFIER_MODEL", "gpt-5.6-luna")
PLANNER_MODEL = os.getenv("PLANNER_MODEL", "gpt-5.6-luna")
REVIEWER_MODEL = os.getenv("REVIEWER_MODEL", "gpt-5.6-luna")
MANAGER_MODEL = os.getenv("MANAGER_MODEL", "gpt-5.6-luna")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing in your .env file.")

if not SCHEMA_FILE.exists():
    raise FileNotFoundError(f"Missing schema file: {SCHEMA_FILE}")


def read_prompt(filename: str) -> str:
    file_path = PROMPTS_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Missing prompt file: {file_path}")
    return file_path.read_text(encoding="utf-8").strip()


def validate_budget_data(data: dict) -> list:
    """Returns a list of problem strings. Empty list means data is valid."""
    problems = []

    required_keys = ["income", "fixed_expenses", "variable_expenses", "debts"]
    for key in required_keys:
        if key not in data:
            problems.append(f"Missing required field: '{key}'")

    income = data.get("income")
    if income is not None:
       if isinstance(income, dict):
        total_income = sum(v for v in income.values() if isinstance(v, (int, float)))
        if total_income <= 0:
            problems.append("Total income (sum of income sources) must be greater than zero.")
    elif isinstance(income, (int, float)):
        if income <= 0:
            problems.append("Income must be a positive number.")
    else:
        problems.append("'income' must be a number or an object of income sources.")

    for list_key in ["fixed_expenses", "variable_expenses", "debts"]:
        value = data.get(list_key)
        if value is not None and not isinstance(value, (list, dict)):
            problems.append(f"'{list_key}' should be a list or object of items.")

    return problems


print("\n===== STEP 1: LOADING & VALIDATING DATA =====")

budget_data = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
validation_problems = validate_budget_data(budget_data)

if validation_problems:
    print("Validation FAILED. Fix these issues in your budget JSON before running again:\n")
    for problem in validation_problems:
        print(" -", problem)
    raise SystemExit(1)

print("Validation passed. Budget data looks structurally sound.")

clarify_prompt = read_prompt("clarify_questions_prompt.md")
system_prompt = read_prompt("budget_agent_system_prompt.md")
planner_prompt = read_prompt("planner_agent_prompt.md")
reviewer_prompt = read_prompt("reviewer_agent_prompt.md")
manager_prompt = read_prompt("manager_agent_prompt.md")

clarifier_llm = LLM(model=CLARIFIER_MODEL, api_key=OPENAI_API_KEY)
planner_llm = LLM(model=PLANNER_MODEL, api_key=OPENAI_API_KEY)
reviewer_llm = LLM(model=REVIEWER_MODEL, api_key=OPENAI_API_KEY)
manager_llm = LLM(model=MANAGER_MODEL, api_key=OPENAI_API_KEY)

print("\n===== MODEL MAP =====")
print("Clarifier Agent ->", CLARIFIER_MODEL)
print("Planner Agent ->", PLANNER_MODEL)
print("Reviewer Agent ->", REVIEWER_MODEL)
print("Manager Agent ->", MANAGER_MODEL)
print("=====================\n")

clarifier_agent = Agent(
    role="Clarification Agent",
    goal="Identify whether the provided budget data is complete enough for analysis.",
    backstory=clarify_prompt,
    llm=clarifier_llm,
    verbose=True
)

planner_agent = Agent(
    role="Budget Planner Agent",
    goal="Analyze the budget and create a realistic financial plan.",
    backstory=f"{system_prompt}\n\n{planner_prompt}",
    llm=planner_llm,
    verbose=True
)

reviewer_agent = Agent(
    role="Budget Reviewer Agent",
    goal="Review the planner's budget analysis for quality, realism, and completeness.",
    backstory=f"{system_prompt}\n\n{reviewer_prompt}",
    llm=reviewer_llm,
    verbose=True
)

manager_agent = Agent(
    role="Budget Manager Agent",
    goal="Produce the final polished budget response for the user.",
    backstory=f"{system_prompt}\n\n{manager_prompt}",
    llm=manager_llm,
    verbose=True
)

clarify_task = Task(
    description=(
        f"""
Review the following budget data and decide whether clarification is needed before analysis.

Budget data:
{json.dumps(budget_data, indent=2)}

Respond with EXACTLY one of these two formats:
1. If the data is complete enough: start your response with the single word "SUFFICIENT" on its own line, then a one-sentence reason.
2. If clarification is needed: start your response with the single word "NEEDS_CLARIFICATION" on its own line, then a numbered list of specific questions.
        """
    ),
    expected_output=(
        "Either 'SUFFICIENT' followed by a short reason, or 'NEEDS_CLARIFICATION' "
        "followed by a numbered list of clarifying questions."
    ),
    agent=clarifier_agent
)


print("===== STEP 2: RUNNING CLARIFIER =====")
start_time = time.time()

clarifier_crew = Crew(
    agents=[clarifier_agent],
    tasks=[clarify_task],
    process=Process.sequential,
    verbose=True
)

clarifier_result = clarifier_crew.kickoff()
clarifier_text = str(clarifier_result)

elapsed = time.time() - start_time
print(f"Clarifier finished in {elapsed:.1f} seconds.\n")

first_line = clarifier_text.strip().splitlines()[0].strip().upper()
if first_line.startswith("NEEDS_CLARIFICATION"):
    print("\n===== RESULT: CLARIFICATION NEEDED =====\n")
    print(clarifier_text)
    print("\nPlease answer the questions above.")
    print("Type yosur combined answer below, then press Enter (one line is fine, or use semicolons to separate answers):\n")

    user_answer = input("Your answers: ").strip()
    budget_data["clarifications"] = user_answer

    print("\nThanks. Using your clarifications and proceeding directly to planning, review, and final report.\n")
else:
    print("Clarifier confirmed data is sufficient. Proceeding to planning, review, and final report.\n")

planner_task = Task(
    description=(
        f"""
Analyze the budget data below and create a realistic monthly budget plan.

Budget data:
{json.dumps(budget_data, indent=2)}
        """
    ),
    expected_output=(
        "A structured budget plan with income, expenses, debt pressure, "
        "leftover cash flow, and practical recommendations."
    ),
    agent=planner_agent
)

reviewer_task = Task(
    description=(
        """
Review the planner agent's output for correctness, completeness, clarity, and realism.
Check whether the plan properly addresses the user's financial situation and goal.
        """
    ),
    expected_output=(
        "A structured review containing strengths, problems found, "
        "corrections, and a final review note."
    ),
    agent=reviewer_agent,
    context=[planner_task]
)

manager_task = Task(
    description=(
        """
Create the final polished budget response by combining the planner's analysis
and the reviewer's feedback into one clear answer for the user.

Your response MUST follow this exact structure with these markdown headings:

## Summary
A 2-3 sentence plain-language overview of the user's financial situation.

## Budget Breakdown
A markdown table with columns: Category | Monthly Amount | Note

## Main Concerns
A short bulleted list of the most important risks or issues.

## Top 3 Actions This Month
A numbered list of exactly 3 concrete, prioritized next steps.
        """
    ),
    expected_output=(
        "A final user-ready budget response following the exact heading structure: "
        "Summary, Budget Breakdown (table), Main Concerns, Top 3 Actions This Month."
    ),
    agent=manager_agent,
    context=[planner_task, reviewer_task]
)

print("===== STEP 3: RUNNING PLANNER, REVIEWER, MANAGER =====")
start_time = time.time()

main_crew = Crew(
    agents=[planner_agent, reviewer_agent, manager_agent],
    tasks=[planner_task, reviewer_task, manager_task],
    process=Process.sequential,
    verbose=True
)

result = main_crew.kickoff()

elapsed = time.time() - start_time
print(f"Planner + Reviewer + Manager finished in {elapsed:.1f} seconds.\n")

print("\n===== FINAL RESULT =====\n")
print(result)