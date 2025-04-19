"""
Test script for the PydanticAI optimizer implementation.

This script tests the basic functionality of the PydanticAI optimizer service.
"""
import asyncio
import logfire
from app.db.session import get_db_session
from app.services.pydanticai_optimizer import get_pydanticai_optimizer_service
from app.schemas.customize import CustomizationLevel
import json
import sys

# Set up logging
logfire.configure(min_level="INFO", sinks=["console"])

async def test_basic_optimization():
    """
    Test the basic optimization functionality.
    """
    # Get the database session
    db = next(get_db_session())
    
    # Get the optimizer service
    optimizer_service = get_pydanticai_optimizer_service(db)
    
    try:
        # Get a resume and job description ID from the database
        # Replace these with actual IDs from your database
        resume_id = "your-resume-id"
        job_id = "your-job-id"
        
        if len(sys.argv) > 2:
            resume_id = sys.argv[1]
            job_id = sys.argv[2]
        
        # Generate a customization plan
        plan = await optimizer_service.generate_customization_plan(
            resume_id=resume_id,
            job_id=job_id,
            customization_strength=CustomizationLevel.BALANCED,
            industry="technology",
            iterations=1
        )
        
        # Print the plan
        print("\n=== Customization Plan ===")
        print(f"Summary: {plan.summary}")
        print(f"Job Analysis: {plan.job_analysis}")
        print(f"Keywords to Add: {', '.join(plan.keywords_to_add)}")
        print(f"Formatting Suggestions: {', '.join(plan.formatting_suggestions)}")
        print(f"Recommendations: {len(plan.recommendations)}")
        
        # Print a sample recommendation
        if plan.recommendations:
            rec = plan.recommendations[0]
            print("\n=== Sample Recommendation ===")
            print(f"Section: {rec.section}")
            print(f"What: {rec.what}")
            print(f"Why: {rec.why}")
            if rec.before_text:
                print(f"Before: {rec.before_text[:100]}...")
            if rec.after_text:
                print(f"After: {rec.after_text[:100]}...")
        
        # Optional: Implement the plan
        if len(sys.argv) > 3 and sys.argv[3] == "--implement":
            print("\n=== Implementing Customization Plan ===")
            result = await optimizer_service.customize_resume(
                resume_id=resume_id,
                job_id=job_id,
                customization_strength=CustomizationLevel.BALANCED,
                industry="technology",
                iterations=2
            )
            
            print(f"Original Resume ID: {result['original_resume_id']}")
            print(f"Customized Resume ID: {result['customized_resume_id']}")
            
            # Save the result to a file for inspection
            with open("customization_result.json", "w") as f:
                json.dump({
                    "original_resume_id": result["original_resume_id"],
                    "customized_resume_id": result["customized_resume_id"],
                    "original_content": result["original_content"],
                    "customized_content": result["customized_content"]
                }, f, indent=2)
            
            print("Customization result saved to customization_result.json")
    
    except Exception as e:
        logfire.error(f"Error testing optimization: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Testing PydanticAI optimizer...")
    asyncio.run(test_basic_optimization())
    print("Test completed.")