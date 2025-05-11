"""
Simple integration test for the model_optimizer module.
"""

import app.services.model_optimizer as mo
from app.services.thinking_budget import TaskComplexity

print("Model Optimizer Integration Test")
print("==================================")

print("\n1. Testing task classification")
complexity, importance = mo.classify_task("resume_evaluation")
print(f"Classified 'resume_evaluation' task as complexity={complexity.value}, importance={importance.value}")

print("\n2. Testing optimized model selection")
model_config = mo.select_optimized_model(
    task_name="resume_evaluation",
    user_override={"cost_sensitivity": 1.2}
)
print(f"Selected model: {model_config['model']}")
print(f"Temperature: {model_config.get('temperature')}")
print(f"Max tokens: {model_config.get('max_tokens')}")
print(f"Has thinking config: {'Yes' if 'thinking_config' in model_config else 'No'}")
print(f"Optimization metadata: {model_config.get('optimization_metadata', {})}")

print("\n3. Testing token usage tracking")
result = mo.track_token_usage(
    model="google:gemini-2.5-pro-preview-03-25",
    task_name="test_task",
    request_id="test_request_id",
    input_tokens=1000,
    output_tokens=500
)
print(f"Tracked tokens - Input: {result['input_tokens']}, Output: {result['output_tokens']}")
print(f"Calculated costs - Input: ${result['input_cost']:.6f}, Output: ${result['output_cost']:.6f}, Total: ${result['total_cost']:.6f}")

print("\n4. Getting cost report")
report = mo.get_cost_report()
print(f"Total tokens: {report['total_tokens']}")
print(f"Total cost: ${report['total_cost']:.6f}")
print(f"Models tracked: {list(report['models'].keys())}")
print(f"Tasks tracked: {list(report['tasks'].keys())}")
print(f"Budget status: {report['budget_status']['overall_status']}")

print("\n5. Testing prompt optimization")
test_prompt = """
This is a test prompt with multiple paragraphs.

It contains several lines of text that could be optimized.

<example>
This is an example that might be removed.
Input: test
Output: result
</example>

In other words, this is a good test case.
"""

simple_optimized = mo.optimize_prompt(test_prompt, TaskComplexity.SIMPLE, exclude_examples=True)
complex_optimized = mo.optimize_prompt(test_prompt, TaskComplexity.COMPLEX, exclude_examples=False)

print(f"Original prompt length: {len(test_prompt)}")
print(f"Simple optimized prompt length: {len(simple_optimized)}")
print(f"Complex optimized prompt length: {len(complex_optimized)}")
print(f"Simple optimization contains examples: {'No' if '<example>' not in simple_optimized else 'Yes'}")
print(f"Complex optimization contains examples: {'No' if '<example>' not in complex_optimized else 'Yes'}")

print("\n6. Resetting cost tracking")
mo.reset_cost_tracking()
report_after_reset = mo.get_cost_report()
print(f"Total tokens after reset: {report_after_reset['total_tokens']}")
print(f"Total cost after reset: ${report_after_reset['total_cost']:.6f}")

print("\nAll tests completed successfully!")