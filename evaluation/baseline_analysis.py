"""Baseline analysis runner for evaluation framework."""

import argparse
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

# Constants
CHART_WIDTH = 50
MIN_SCORE = 0.0
MAX_SCORE = 1.0


async def run_baseline(dataset_path: Path, output_dir: Path) -> None:
    """Run comprehensive evaluation on the provided dataset.

    Args:
        dataset_path: Path to the test dataset file.
        output_dir: Directory to store baseline results.
    """
    logger = get_evaluation_logger("BaselineAnalysis")

    try:
        dataset = load_test_dataset(dataset_path)
    except Exception as e:
        logger.error(f"Failed to load test dataset from {dataset_path}: {e}")
        raise

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
        try:
            actual_output = {
                "resume_content": case.resume_content,
                "job_description": case.job_description,
                "optimization_applied": False,
            }
            result = await pipeline.evaluate(case, actual_output, case.id)
            aggregator.add_result(result)
        except Exception as e:
            logger.error(f"Failed to evaluate case {case.id}: {e}")
            continue

    summary = aggregator.aggregate()

    analyzer = PerformanceAnalyzer(aggregator.results)
    trends = analyzer.analyze_trends()
    failures = analyzer.identify_failure_patterns()

    reporter = EvaluationReporter(aggregator.results)
    report_md = reporter.generate_summary_report()

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        logger.error(f"Failed to create output directory {output_dir}: {e}")
        raise

    try:
        with open(output_dir / "baseline_summary.md", "w") as f:
            f.write(report_md)
    except (OSError, PermissionError) as e:
        logger.error(f"Failed to write baseline summary: {e}")
        raise

    metrics: Dict[str, Any] = {
        "summary": summary,
        "trends": trends,
        "failures": failures,
    }
    try:
        with open(output_dir / "baseline_metrics.json", "w") as f:
            json.dump(metrics, f, indent=2)
    except (OSError, PermissionError) as e:
        logger.error(f"Failed to write baseline metrics: {e}")
        raise

    # Simple text-based visualization of average evaluator scores
    names = list(summary["evaluator_breakdown"].keys())
    scores = [summary["evaluator_breakdown"][n]["average_score"] for n in names]

    chart_lines = []
    for name, score in zip(names, scores):
        # Validate score and clamp to valid range
        validated_score = max(MIN_SCORE, min(MAX_SCORE, score))
        bar = "#" * int(validated_score * CHART_WIDTH)
        chart_lines.append(f"{name:20} | {bar} {score:.2f}")

    try:
        with open(output_dir / "score_chart.txt", "w") as chart_file:
            chart_file.write("Average Evaluator Scores\n")
            chart_file.write("\n".join(chart_lines))
    except (OSError, PermissionError) as e:
        logger.error(f"Failed to write score chart: {e}")
        raise

    logger.info("Baseline analysis completed")


def main() -> None:
    """Entry point for command-line execution.
    
    Usage examples:
        python -m evaluation.baseline_analysis
        python -m evaluation.baseline_analysis --dataset custom_dataset.yaml --output custom_results
        python -m evaluation.baseline_analysis --help
    """
    parser = argparse.ArgumentParser(
        description="Run baseline evaluation analysis on test datasets",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Get project root for proper path resolution
    project_root = Path(__file__).parent.parent
    default_dataset = project_root / "evaluation" / "test_data" / "datasets" / "curated_test_dataset.yaml"
    default_output = project_root / "baseline_results"
    
    parser.add_argument(
        "--dataset", 
        type=Path, 
        default=default_dataset,
        help="Path to test dataset file (YAML format)"
    )
    parser.add_argument(
        "--output", 
        type=Path, 
        default=default_output,
        help="Directory to store baseline results"
    )
    
    args = parser.parse_args()
    
    # Ensure absolute paths
    dataset_path = args.dataset.resolve()
    output_path = args.output.resolve()
    
    try:
        asyncio.run(run_baseline(dataset_path, output_path))
    except KeyboardInterrupt:
        print("\nBaseline analysis interrupted by user")
    except Exception as e:
        print(f"Error running baseline analysis: {e}")
        exit(1)


if __name__ == "__main__":
    main()
