"""
pyagent-evals: Evaluation framework for agent quality.

Mirrors pi-mono's packages/evals — provides a test harness for
running prompts through the agent and asserting on the results,
plus LangSmith integration for cloud-based evaluation & monitoring.
"""

from pyagent_evals.runner import EvalCase, EvalRunner, EvalResult
from pyagent_evals.langsmith_eval import (
    EVAL_DATASET,
    EvalExample,
    upload_eval_dataset,
    run_evals_with_metrics,
    compute_metrics,
    print_eval_report,
    run_langsmith_evals,
)

__all__ = [
    "EvalCase",
    "EvalRunner",
    "EvalResult",
    "EVAL_DATASET",
    "EvalExample",
    "upload_eval_dataset",
    "run_evals_with_metrics",
    "compute_metrics",
    "print_eval_report",
    "run_langsmith_evals",
]
