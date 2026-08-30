"""python-vibe: a deterministic harness around a small local model.

The model drafts; the harness decides what ships.

    from harness import Agent, AgentOptions

    agent = Agent(AgentOptions(project=Path("~/app"), scope="src"))
    result = agent.run("add multiply(a, b) and a unit test")
    print(result.summary, result.writes)

Read-only is one flag:

    AgentOptions(project=..., allow_writes=False)

Command line and HTTP are the same object:

    python -m harness run ~/app "fix the NameError"
    python -m harness serve --project ~/app
"""

from harness.agent import Agent, AgentOptions, AgentResult, Question, Step

# The one thing the command line needs from the model package. Going
# through here keeps that package's shape private: the CLI and the
# server do not import harness.model.* directly.
from harness.model.route import route_advice
from harness.guard.python_vibe import PythonVibeGuard
from harness.guard.run import complete
from harness.guard.types import Finding, Outcome

__all__ = [
    "Agent",
    "AgentOptions",
    "route_advice",
    "AgentResult",
    "Question",
    "Step",
    "PythonVibeGuard",
    "complete",
    "Finding",
    "Outcome",
]
