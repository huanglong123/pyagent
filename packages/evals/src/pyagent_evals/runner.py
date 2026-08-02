"""
Evaluation runner — execute prompts and assert on results.

Provides an EvalCase and EvalRunner framework for testing agent
behavior. Each eval case specifies a prompt and an assertion function
that checks the agent's response.

Mirrors pi-mono's eval framework which uses structured test cases
to validate agent behavior across scenarios.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from rich.console import Console
from rich.table import Table

from pyagent_ai import ProviderConfig
from pyagent_agent import AgentSession

logger = logging.getLogger(__name__)


@dataclass
class EvalCase:
    """A single evaluation test case.

    name: Short identifier for the case.
    prompt: The prompt to send to the agent.
    assert_fn: Function that receives the response string and returns True/False.
    description: Optional longer description.
    """

    name: str
    prompt: str
    assert_fn: Callable[[str], bool]
    description: str = ""


@dataclass
class EvalResult:
    """Result of running a single eval case.

    case: The eval case that was run.
    passed: Whether the assertion passed.
    response: The agent's response text.
    error: Error message if the agent failed.
    duration_ms: Time taken in milliseconds.
    """

    case: EvalCase
    passed: bool
    response: str = ""
    error: str | None = None
    duration_ms: float = 0.0


class EvalRunner:
    """Runs evaluation cases against an agent session.

    Usage:
        runner = EvalRunner(config=ProviderConfig(...))
        runner.add_case(EvalCase(name="math", prompt="What is 2+2?", assert_fn=lambda r: "4" in r))
        results = runner.run()
        runner.print_report(results)
    """

    def __init__(self, config: ProviderConfig | None = None) -> None:
        self.config = config or ProviderConfig()
        self._cases: list[EvalCase] = []
        self.console = Console()

    def add_case(self, case: EvalCase) -> None:
        """Add an evaluation case."""
        self._cases.append(case)

    def add_case_simple(
        self,
        name: str,
        prompt: str,
        assert_fn: Callable[[str], bool],
        description: str = "",
    ) -> None:
        """Add a simple eval case."""
        self.add_case(EvalCase(name=name, prompt=prompt, assert_fn=assert_fn, description=description))

    def run(self) -> list[EvalResult]:
        """Run all eval cases and return results."""
        results = []
        for case in self._cases:
            self.console.print(f"[dim]Running eval: {case.name}[/]")
            session = AgentSession(model_config=self.config, tools=None)

            import time

            start = time.time()
            try:
                response = session.run(case.prompt)
                elapsed = (time.time() - start) * 1000
                passed = case.assert_fn(response)
                results.append(
                    EvalResult(
                        case=case,
                        passed=passed,
                        response=response,
                        duration_ms=elapsed,
                    )
                )
            except Exception as e:
                # Persist the full traceback to the error log file.
                logger.exception("Eval case '%s' failed", case.name)
                elapsed = (time.time() - start) * 1000
                results.append(
                    EvalResult(
                        case=case,
                        passed=False,
                        error=str(e),
                        duration_ms=elapsed,
                    )
                )

        return results

    @staticmethod
    def print_report(results: list[EvalResult], console: Console | None = None) -> None:
        """Print a summary table of eval results."""
        console = console or Console()

        table = Table(title="Eval Results")
        table.add_column("Name", style="cyan")
        table.add_column("Status")
        table.add_column("Duration (ms)", justify="right")
        table.add_column("Error", style="red")

        passed_count = 0
        for result in results:
            status = "[green]PASS[/]" if result.passed else "[red]FAIL[/]"
            if result.passed:
                passed_count += 1
            table.add_row(
                result.case.name,
                status,
                f"{result.duration_ms:.0f}",
                result.error or "",
            )

        console.print(table)
        console.print(
            f"\n[bold]{passed_count}/{len(results)}[/] evals passed "
            f"({'green' if passed_count == len(results) else 'yellow'})"
        )
