#!/usr/bin/env python
"""
Smart Request Handler Demo Script

This script demonstrates the capabilities of the smart request handler
by sending requests with different priorities and complexities and
showing the monitoring information.

Usage:
    python demo_smart_request.py

Options:
    --url BASE_URL     Base URL for the API (default: http://localhost:5001)
    --concurrent N     Number of concurrent requests to send (default: 5)
    --iterations N     Number of test iterations to run (default: 3)
    --show-stats       Show detailed statistics after tests
"""

import argparse
import asyncio
import json
import time
import random
import httpx
from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TaskID
from rich.panel import Panel

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Smart Request Handler Demo")
parser.add_argument("--url", default="http://localhost:5001", help="Base URL for the API")
parser.add_argument("--concurrent", type=int, default=5, help="Number of concurrent requests")
parser.add_argument("--iterations", type=int, default=3, help="Number of test iterations")
parser.add_argument("--show-stats", action="store_true", help="Show detailed statistics")
args = parser.parse_args()

# Set up console for rich output
console = Console()

# Test data
test_resume_id = "test-resume-id"
test_job_id = "test-job-id"

# Endpoint configuration
endpoints = [
    {
        "name": "ATS Analysis",
        "path": "/api/v1/ats/analyze",
        "method": "POST",
        "json": {"resume_id": test_resume_id, "job_description_id": test_job_id},
        "priority": "HIGH",
        "complexity": "MODERATE"
    },
    {
        "name": "ATS Plan",
        "path": "/api/v1/ats/analyze-and-plan",
        "method": "POST",
        "json": {"resume_id": test_resume_id, "job_description_id": test_job_id},
        "priority": "CRITICAL",
        "complexity": "COMPLEX"
    },
    {
        "name": "Health Check",
        "path": "/api/v1/stats/health",
        "method": "GET",
        "json": None,
        "priority": "LOW",
        "complexity": "SIMPLE"
    }
]

# Store results for analysis
results = []
request_ids = []

async def send_request(
    client: httpx.AsyncClient,
    endpoint: Dict[str, Any],
    progress: Optional[Progress] = None,
    task_id: Optional[TaskID] = None
) -> Dict[str, Any]:
    """Send a request to the API and track the result."""
    start_time = time.time()
    
    try:
        if endpoint["method"] == "POST":
            response = await client.post(
                f"{args.url}{endpoint['path']}",
                json=endpoint['json']
            )
        else:
            response = await client.get(f"{args.url}{endpoint['path']}")
        
        duration = time.time() - start_time
        
        # Update progress if provided
        if progress and task_id:
            progress.update(task_id, advance=1)
        
        # Extract request ID if present
        request_id = None
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "request_id" in data:
                request_id = data["request_id"]
                request_ids.append(request_id)
        
        return {
            "endpoint": endpoint["name"],
            "path": endpoint["path"],
            "priority": endpoint["priority"],
            "complexity": endpoint["complexity"],
            "status_code": response.status_code,
            "duration": duration,
            "request_id": request_id,
            "success": response.status_code < 400
        }
    except Exception as e:
        duration = time.time() - start_time
        
        # Update progress if provided
        if progress and task_id:
            progress.update(task_id, advance=1)
            
        return {
            "endpoint": endpoint["name"],
            "path": endpoint["path"],
            "priority": endpoint["priority"],
            "complexity": endpoint["complexity"],
            "status_code": 0,
            "duration": duration,
            "error": str(e),
            "success": False
        }

async def run_test_iteration(iteration: int) -> List[Dict[str, Any]]:
    """Run a single test iteration with concurrent requests."""
    iteration_results = []
    
    # Create a client for the requests
    async with httpx.AsyncClient(timeout=30.0) as client:
        with Progress() as progress:
            # Create a task for tracking progress
            task = progress.add_task(
                f"[cyan]Running iteration {iteration+1}/{args.iterations}...", 
                total=args.concurrent
            )
            
            # Create random endpoint requests
            tasks = []
            for i in range(args.concurrent):
                # Choose a random endpoint
                endpoint = random.choice(endpoints)
                
                # Send the request
                task_coro = send_request(client, endpoint, progress, task)
                tasks.append(task_coro)
            
            # Wait for all requests to complete
            batch_results = await asyncio.gather(*tasks)
            iteration_results.extend(batch_results)
    
    return iteration_results

async def get_request_statistics() -> Dict[str, Any]:
    """Get request statistics from the API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{args.url}/api/v1/stats/requests")
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to get statistics: {response.status_code}"}
    except Exception as e:
        return {"error": f"Error getting statistics: {str(e)}"}

async def get_request_details(request_id: str) -> Dict[str, Any]:
    """Get details for a specific request."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{args.url}/api/v1/stats/request/{request_id}")
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to get request details: {response.status_code}"}
    except Exception as e:
        return {"error": f"Error getting request details: {str(e)}"}

def print_results_table(all_results: List[Dict[str, Any]]) -> None:
    """Print a table of test results."""
    table = Table(title="Smart Request Test Results")
    
    table.add_column("Endpoint", style="cyan")
    table.add_column("Priority", style="magenta")
    table.add_column("Complexity", style="yellow")
    table.add_column("Status", style="green")
    table.add_column("Duration (s)", style="blue")
    table.add_column("Request ID", style="dim")
    
    for result in all_results:
        status = "[green]Success" if result.get("success", False) else f"[red]Failed ({result.get('status_code', 'Error')})"
        
        table.add_row(
            result["endpoint"],
            result["priority"],
            result["complexity"],
            status,
            f"{result.get('duration', 0):.4f}",
            result.get("request_id", "N/A")
        )
    
    console.print(table)

def print_statistics(stats: Dict[str, Any]) -> None:
    """Print request statistics."""
    if "error" in stats:
        console.print(f"[red]Error getting statistics: {stats['error']}")
        return
    
    console.print(Panel(f"[bold cyan]Request Statistics", title="Smart Request Handler"))
    
    # Print general statistics
    console.print(f"[bold]Total Requests:[/bold] {stats.get('total_requests', 0)}")
    console.print(f"[bold]Completed Requests:[/bold] {stats.get('completed_requests', 0)}")
    console.print(f"[bold]Failed Requests:[/bold] {stats.get('failed_requests', 0)}")
    console.print(f"[bold]Active Requests:[/bold] {stats.get('active_requests', 0)}")
    console.print(f"[bold]Success Rate:[/bold] {stats.get('success_rate', 0):.2f}%")
    
    # Print response time statistics
    if "response_times" in stats:
        console.print("\n[bold cyan]Response Times[/bold cyan]")
        times = stats["response_times"]
        console.print(f"[bold]Min:[/bold] {times.get('min', 0):.4f}s")
        console.print(f"[bold]Max:[/bold] {times.get('max', 0):.4f}s")
        console.print(f"[bold]Avg:[/bold] {times.get('avg', 0):.4f}s")
        console.print(f"[bold]p95:[/bold] {times.get('p95', 0):.4f}s")
    
    # Print endpoint statistics
    if "endpoints" in stats and stats["endpoints"]:
        table = Table(title="Endpoint Statistics")
        table.add_column("Endpoint", style="cyan")
        table.add_column("Total", style="blue")
        table.add_column("Completed", style="green")
        table.add_column("Failed", style="red")
        table.add_column("Active", style="yellow")
        table.add_column("Avg Duration", style="magenta")
        
        for path, endpoint_stats in stats["endpoints"].items():
            table.add_row(
                path,
                str(endpoint_stats.get("total_requests", 0)),
                str(endpoint_stats.get("completed_requests", 0)),
                str(endpoint_stats.get("failed_requests", 0)),
                str(endpoint_stats.get("active_requests", 0)),
                f"{endpoint_stats.get('avg_duration', 0):.4f}s"
            )
        
        console.print("\n")
        console.print(table)

async def main() -> None:
    """Run the demo script."""
    console.print(Panel(f"[bold]Smart Request Handler Demo[/bold]\nRunning with {args.concurrent} concurrent requests per iteration, {args.iterations} iterations", title="Starting Test"))
    
    # Run test iterations
    for i in range(args.iterations):
        iteration_results = await run_test_iteration(i)
        results.extend(iteration_results)
        
        # Small delay between iterations
        if i < args.iterations - 1:
            await asyncio.sleep(1)
    
    # Print results table
    print_results_table(results)
    
    # Show statistics if requested
    if args.show_stats:
        console.print("\n[cyan]Fetching request statistics...[/cyan]")
        stats = await get_request_statistics()
        print_statistics(stats)
        
        # Show some specific request details if available
        if request_ids and len(request_ids) > 0:
            sample_request_id = request_ids[0]
            console.print(f"\n[cyan]Fetching details for request {sample_request_id}...[/cyan]")
            details = await get_request_details(sample_request_id)
            
            if "error" not in details:
                console.print(Panel(f"[bold]Request Details[/bold]\nID: {sample_request_id}", title="Sample Request"))
                console.print(json.dumps(details, indent=2))
            else:
                console.print(f"[red]Error fetching request details: {details['error']}[/red]")

if __name__ == "__main__":
    asyncio.run(main())