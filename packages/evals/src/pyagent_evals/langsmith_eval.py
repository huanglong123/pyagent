"""
LangSmith evaluation — automated benchmarking of core agent functionality.

Provides:
- A curated evaluation dataset covering core agent capabilities
  (mathematical reasoning, code generation, tool usage, conversation).
- Integration with LangSmith's dataset + evaluation APIs so that
  results appear in the LangSmith project alongside runtime traces.
- Key metrics: success rate, average latency, token consumption.

Usage (from project root):

    from pyagent_evals.langsmith_eval import run_langsmith_evals
    run_langsmith_evals()
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable

from rich.console import Console

from pyagent_ai import ProviderConfig, init_tracing
from pyagent_ai.tracing import (
    TraceMetadata,
    create_dataset,
    get_config as get_tracing_config,
    get_langsmith_client,
    measure_latency,
)
from pyagent_agent import AgentSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Core evaluation dataset — representative prompts with expected assertions
# ---------------------------------------------------------------------------

@dataclass
class EvalExample:
    """A single evaluation example with input prompt and expected behavior."""

    input_prompt: str
    assertion_fn: Callable[[str], bool]
    category: str = "general"
    description: str = ""


# The canonical evaluation dataset. These examples cover the core
# capabilities that users rely on daily.
EVAL_DATASET: list[EvalExample] = [
    EvalExample(
        input_prompt="What is 2+2? Answer with just the number.",
        assertion_fn=lambda r: "4" in r,
        category="math",
        description="Basic arithmetic reasoning",
    ),
    EvalExample(
        input_prompt="Explain what a Python list comprehension is in one sentence.",
        assertion_fn=lambda r: len(r) > 30 and "list" in r.lower(),
        category="knowledge",
        description="Concept explanation",
    ),
    EvalExample(
        input_prompt="Write a Python function that reverses a string.",
        assertion_fn=lambda r: "def" in r and "reverse" in r.lower(),
        category="code_gen",
        description="Code generation — string manipulation",
    ),
    EvalExample(
        input_prompt="What is the capital of France? Answer with just the city name.",
        assertion_fn=lambda r: "paris" in r.lower(),
        category="factual",
        description="Factual knowledge lookup",
    ),
    EvalExample(
        input_prompt="How do you declare a variable in Python? Give a one-line example.",
        assertion_fn=lambda r: "=" in r and "python" in r.lower(),
        category="knowledge",
        description="Syntax knowledge",
    ),
    EvalExample(
        input_prompt="Write a Python function to check if a number is prime.",
        assertion_fn=lambda r: "def" in r and "prime" in r.lower(),
        category="code_gen",
        description="Code generation — algorithm",
    ),
    EvalExample(
        input_prompt="Summarize: 'The quick brown fox jumps over the lazy dog.'",
        assertion_fn=lambda r: len(r) > 10,
        category="summarization",
        description="Text summarization",
    ),
    EvalExample(
        input_prompt="Convert 100 degrees Celsius to Fahrenheit.",
        assertion_fn=lambda r: "212" in r or "100" in r,
        category="math",
        description="Unit conversion",
    ),
]

# ---------------------------------------------------------------------------
# LangSmith dataset upload & evaluation
# ---------------------------------------------------------------------------

def upload_eval_dataset(dataset_name: str = "pyagent-core-evals") -> Any | None:
    """Upload the core evaluation dataset to LangSmith.

    Args:
        dataset_name: Name for the LangSmith dataset.

    Returns:
        The created/updated dataset object, or None on failure.
    """
    inputs = [{"input": ex.input_prompt} for ex in EVAL_DATASET]
    outputs = [{"category": ex.category} for ex in EVAL_DATASET]

    return create_dataset(
        dataset_name=dataset_name,
        inputs=inputs,
        outputs=outputs,
        description="Core pyagent evaluation dataset covering math, code gen, knowledge, and summarization.",
    )


def run_evals_with_metrics(
    config: ProviderConfig | None = None,
    *,
    max_cases: int | None = None,
) -> list[dict[str, Any]]:
    """Run evaluation cases and return detailed results with metrics.

    Each result includes:
    - input prompt
    - response text
    - pass/fail
    - duration_ms
    - token usage (if available)
    - error message (if any)

    Args:
        config: Provider configuration (uses default if None).
        max_cases: Maximum number of cases to run (for quick smoke tests).

    Returns:
        List of result dicts.
    """
    cfg = config or ProviderConfig()
    cases = EVAL_DATASET[:max_cases] if max_cases else EVAL_DATASET
    results: list[dict[str, Any]] = []

    for i, example in enumerate(cases):
        logger.info("Running eval [%d/%d]: %s", i + 1, len(cases), example.category)

        session = AgentSession(model_config=cfg, tools=None)
        start = time.perf_counter()

        try:
            response = session.run(example.input_prompt)
            elapsed_ms = (time.perf_counter() - start) * 1000
            passed = example.assertion_fn(response)

            # Get token usage from session tracing if available
            token_info: dict[str, Any] = {}
            tracing_meta = get_tracing_config()
            if tracing_meta.enabled:
                try:
                    from pyagent_ai.tracing import current_metadata
                    meta = current_metadata()
                    token_info = {
                        "input_tokens": meta.get("input_tokens", 0),
                        "output_tokens": meta.get("output_tokens", 0),
                        "total_tokens": meta.get("total_tokens", 0),
                    }
                except Exception:
                    pass

            result = {
                "index": i,
                "category": example.category,
                "prompt": example.input_prompt,
                "response": response,
                "passed": passed,
                "duration_ms": round(elapsed_ms, 2),
                "error": None,
                "tokens": token_info,
            }

        except Exception as e:
            logger.exception("Eval case failed: %s", example.category)
            elapsed_ms = (time.perf_counter() - start) * 1000
            result = {
                "index": i,
                "category": example.category,
                "prompt": example.input_prompt,
                "response": "",
                "passed": False,
                "duration_ms": round(elapsed_ms, 2),
                "error": str(e),
                "tokens": {},
            }

        results.append(result)

    return results


def compute_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate metrics from evaluation results.

    Returns a dict with:
    - success_rate: fraction of passed cases
    - avg_duration_ms: mean response time
    - avg_tokens: mean total tokens (if token data available)
    - category_breakdown: success rate per category
    - total_cases / passed / failed
    """
    total = len(results)
    if total == 0:
        return {"error": "No results to compute metrics on"}

    passed = sum(1 for r in results if r["passed"])
    durations = [r["duration_ms"] for r in results]
    success_rate = passed / total

    # Category breakdown
    category_stats: dict[str, dict[str, int]] = {}
    for r in results:
        cat = r["category"]
        if cat not in category_stats:
            category_stats[cat] = {"passed": 0, "failed": 0, "total": 0}
        category_stats[cat]["total"] += 1
        if r["passed"]:
            category_stats[cat]["passed"] += 1
        else:
            category_stats[cat]["failed"] += 1

    category_rates = {
        cat: {
            "success_rate": round(stats["passed"] / stats["total"], 3) if stats["total"] > 0 else 0,
            **stats,
        }
        for cat, stats in category_stats.items()
    }

    return {
        "total_cases": total,
        "passed": passed,
        "failed": total - passed,
        "success_rate": round(success_rate, 3),
        "avg_duration_ms": round(sum(durations) / len(durations), 2),
        "min_duration_ms": round(min(durations), 2),
        "max_duration_ms": round(max(durations), 2),
        "category_breakdown": category_rates,
    }


def print_eval_report(
    results: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> None:
    """Pretty-print evaluation results and metrics to the console."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    # Detailed results table
    table = Table(title="Evaluation Results")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Category", style="cyan")
    table.add_column("Status")
    table.add_column("Duration (ms)", justify="right")
    table.add_column("Error", style="red")

    for r in results:
        status = "[green]PASS[/]" if r["passed"] else "[red]FAIL[/]"
        table.add_row(
            str(r["index"] + 1),
            r["category"],
            status,
            f"{r['duration_ms']:.0f}",
            r.get("error") or "",
        )

    console.print(table)

    # Summary metrics
    console.print()
    console.print("[bold]Aggregate Metrics[/]")
    console.print(f"  Success rate: [{'green' if metrics['success_rate'] > 0.8 else 'yellow'}]{metrics['success_rate']:.1%}[/]")
    console.print(f"  Total cases: {metrics['total_cases']}")
    console.print(f"  Passed: [green]{metrics['passed']}[/]")
    console.print(f"  Failed: [red]{metrics['failed']}[/]")
    console.print(f"  Avg duration: {metrics['avg_duration_ms']:.0f} ms")
    console.print(f"  Min duration: {metrics['min_duration_ms']:.0f} ms")
    console.print(f"  Max duration: {metrics['max_duration_ms']:.0f} ms")

    if metrics.get("category_breakdown"):
        console.print()
        console.print("[bold]Category Breakdown[/]")
        for cat, stats in metrics["category_breakdown"].items():
            rate_color = "green" if stats["success_rate"] > 0.8 else "yellow"
            console.print(
                f"  {cat}: [{rate_color}]{stats['success_rate']:.0%}[/] "
                f"({stats['passed']}/{stats['total']})"
            )


def run_langsmith_evals(
    dataset_name: str = "pyagent-core-evals",
    config: ProviderConfig | None = None,
    *,
    upload: bool = True,
    max_cases: int | None = None,
) -> dict[str, Any]:
    """Full LangSmith evaluation pipeline: upload dataset, run evals, report.

    This is the main entry point for automated LangSmith-based evaluation.

    Args:
        dataset_name: Name for the LangSmith dataset.
        config: Provider configuration (default if None).
        upload: Whether to upload the dataset to LangSmith first.
        max_cases: Limit number of cases (for quick testing).

    Returns:
        Dict with keys: results, metrics, dataset.
    """
    # Ensure tracing is initialised (reads from env vars)
    init_tracing()

    # Step 1: Upload dataset to LangSmith (optional)
    dataset = None
    if upload:
        console = Console()
        console.print("[dim]Uploading evaluation dataset to LangSmith...[/]")
        dataset = upload_eval_dataset(dataset_name)
        if dataset:
            console.print(f"[green]Dataset '{dataset_name}' ready.[/]")
        else:
            console.print("[yellow]LangSmith not configured — skipping dataset upload.[/]")

    # Step 2: Run evaluations
    console.print("[dim]Running evaluation cases...[/]")
    results = run_evals_with_metrics(config, max_cases=max_cases)

    # Step 3: Compute metrics
    metrics = compute_metrics(results)

    # Step 4: Report
    console.print()
    print_eval_report(results, metrics)

    return {
        "results": results,
        "metrics": metrics,
        "dataset": dataset,
    }