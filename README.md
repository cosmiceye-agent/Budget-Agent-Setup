# Budget Agent

A multi-agent personal budgeting project built for agent orchestration practice.

This project is designed to help a user:
- track income from a main job and optional second job,
- organize fixed and variable expenses,
- track debt balances and minimum payments,
- estimate leftover money after monthly obligations,
- detect overspending risks,
- suggest whether leftover money should go to savings, emergency fund, debt payoff, or investments.

## Project Structure

```text
budget-agent/
├── README.md
├── .gitignore
├── .env
├── .env.example
├── prompts/
│   ├── budget_agent_system_prompt.md
│   ├── planner_agent_prompt.md
│   ├── reviewer_agent_prompt.md
│   ├── manager_agent_prompt.md
│   └── clarifying_questions_prompt.md
├── schemas/
│   └── budget_input_schema.json
├── src/
│   └── main.py
└── requirements.txt
```

## Agents

This project uses a 3-agent workflow:

- Planner Agent: creates the first monthly financial plan.
- Reviewer Agent: checks the plan for realism, risk, and missing warnings.
- Manager Agent: produces the final user-facing output.

## Input Categories

The system expects structured monthly inputs for:

- Income
- Fixed expenses
- Variable expenses
- Debt
- Savings
- Investments
- User priority

## Environment Variables

Create a `.env` file in the project root.

Example:

```env
OPENAI_API_KEY=your_real_openai_api_key_here
MODEL_NAME=gpt-5.6-luna
SERPER_API_KEY=your_real_serper_api_key_here
```

Do not commit `.env` to GitHub.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies from `requirements.txt`.
3. Add your API keys to `.env`.
4. Review the prompts in the `prompts/` folder.
5. Run `src/main.py`.

## Status



## Dependencies

- `crewai`: multi-agent framework for defining agents, tasks, and crews.
- `serperai`: optional search API client for future external data lookups.
- `python-dotenv`: loads environment variables from `.env` to keep secrets out of code.
- `openai`: OpenAI Python client used by CrewAI and the agents for LLM calls.

Current stage:
- Prompt design completed
- Schema design completed
- Next step: implement the first working agent flow