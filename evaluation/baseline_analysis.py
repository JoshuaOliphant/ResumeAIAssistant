"""Baseline analysis runner for evaluation framework."""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict

from evaluation.pipeline import EvaluationPipeline, PipelineConfiguration, PipelineMode
from evaluation.test_data.loaders import load_test_dataset
from evaluation.results.aggregator import ResultAggregator
from evaluation.results.analyzer import PerformanceAnalyzer
from evaluation.results.reporter import EvaluationReporter
from evaluation.utils.logger import get_evaluation_logger


async def run_baseline(dataset_path: Path, output_dir: Path) -> None:
    """Run comprehensive evaluation on the provided dataset.

    Args:
        dataset_path: Path to the test dataset file.
        output_dir: Directory to store baseline results.
    """
    logger = get_evaluation_logger("BaselineAnalysis")

    dataset = load_test_dataset(dataset_path)
    config = PipelineConfiguration(
        mode=PipelineMode.COMPREHENSIVE,
        parallel_execution=True,
        max_concurrent_evaluators=3,
        save_intermediate_results=True,
        output_directory=output_dir,
    )
    pipeline = EvaluationPipeline(config)

    aggregator = ResultAggregator()

    for case in dataset.test_cases:
        actual_output = {
            "resume_content": case.resume_content,
            "job_description": case.job_description,
            "optimization_applied": False,
        }
        result = await pipeline.evaluate(case, actual_output, case.id)
        aggregator.add_result(result)

    summary = aggregator.aggregate()

    analyzer = PerformanceAnalyzer(aggregator.results)
    trends = analyzer.analyze_trends()
    failures = analyzer.identify_failure_patterns()

    reporter = EvaluationReporter(aggregator.results)
    report_md = reporter.generate_summary_report()

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "baseline_summary.md", "w") as f:
        f.write(report_md)

    metrics: Dict[str, Any] = {
        "summary": summary,
        "trends": trends,
        "failures": failures,
    }
    with open(output_dir / "baseline_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # Simple text-based visualization of average evaluator scores
    names = list(summary["evaluator_breakdown"].keys())
    scores = [summary["evaluator_breakdown"][n]["average_score"] for n in names]

    chart_lines = []
    for name, score in zip(names, scores):
        bar = "#" * int(score * 50)
        chart_lines.append(f"{name:20} | {bar} {score:.2f}")

    with open(output_dir / "score_chart.txt", "w") as chart_file:
        chart_file.write("Average Evaluator Scores\n")
        chart_file.write("\n".join(chart_lines))

    logger.info("Baseline analysis completed")


def main() -> None:
    """Entry point for command-line execution."""
    dataset_file = Path("evaluation/test_data/datasets/curated_test_dataset.yaml")
    output_dir = Path("baseline_results")
    asyncio.run(run_baseline(dataset_file, output_dir))


if __name__ == "__main__":
    main()
