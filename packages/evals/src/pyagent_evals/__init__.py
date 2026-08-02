"""
pyagent-evals: Evaluation framework for agent quality.

Mirrors pi-mono's packages/evals — provides a test harness for
running prompts through the agent and asserting on the results.
"""

from pyagent_evals.runner import EvalCase, EvalRunner, EvalResult

__all__ = ["EvalCase", "EvalRunner", "EvalResult"]
