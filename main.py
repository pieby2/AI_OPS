"""
AI Operations Assistant - Main Application
FastAPI server that orchestrates multi-agent task execution
"""
import os
import time
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from agents import PlannerAgent, ExecutorAgent, VerifierAgent
from metrics import get_metrics_tracker
from cache import get_cache_manager

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="AI Operations Assistant",
    description="Multi-agent system for executing natural language tasks",
    version="2.0.0"
)

# Request/Response models
class TaskRequest(BaseModel):
    task: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "task": "What's the weather in London and find popular Python web frameworks on GitHub"
            }
        }


class MetricsResponse(BaseModel):
    total_tokens_in: int
    total_tokens_out: int
    total_tokens: int
    estimated_cost_usd: float
    llm_calls: int


class TaskResponse(BaseModel):
    status: str
    task: str
    plan: Dict[str, Any]
    execution_results: list
    final_answer: str
    execution_time: float
    metrics: Optional[MetricsResponse] = None


# Initialize agents (lazy loading to handle env var issues)
planner = None
executor = None
verifier = None


def get_agents():
    """Initialize agents on first request"""
    global planner, executor, verifier
    
    if planner is None:
        try:
            planner = PlannerAgent()
            executor = ExecutorAgent()
            verifier = VerifierAgent()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize agents: {str(e)}. Please check your .env configuration."
            )
    
    return planner, executor, verifier


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "AI Operations Assistant is ready",
        "version": "2.0.0",
        "features": ["caching", "metrics", "news_api"],
        "endpoints": {
            "POST /task": "Submit a task for execution",
            "GET /health": "Check system health",
            "GET /metrics": "Get cumulative usage metrics",
            "GET /cache/stats": "Get cache statistics"
        }
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    try:
        # Check if environment variables are set
        required_vars = ["OPENAI_API_KEY", "GITHUB_TOKEN", "OPENWEATHER_API_KEY"]
        optional_vars = ["NEWS_API_KEY"]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        missing_optional = [var for var in optional_vars if not os.getenv(var)]
        
        if missing_vars:
            return {
                "status": "degraded",
                "message": f"Missing required environment variables: {', '.join(missing_vars)}",
                "missing_optional": missing_optional,
                "agents_initialized": planner is not None
            }
        
        return {
            "status": "healthy",
            "message": "All systems operational",
            "agents_initialized": planner is not None,
            "missing_optional": missing_optional
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@app.get("/metrics")
async def get_metrics():
    """Get cumulative usage metrics"""
    metrics = get_metrics_tracker()
    return metrics.get_total_metrics()


@app.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    cache = get_cache_manager()
    return cache.get_stats()


@app.post("/cache/clear")
async def clear_cache():
    """Clear all cached responses"""
    cache = get_cache_manager()
    count = cache.clear()
    return {"message": f"Cleared {count} cached entries"}


@app.post("/task", response_model=TaskResponse)
async def execute_task(request: TaskRequest):
    """
    Execute a natural language task using the multi-agent system
    
    Process:
    1. Planner Agent creates execution plan
    2. Executor Agent runs each step
    3. Verifier Agent validates and formats results
    """
    start_time = time.time()
    
    # Start metrics tracking for this request
    metrics_tracker = get_metrics_tracker()
    metrics_tracker.start_request()
    
    try:
        # Get or initialize agents
        planner_agent, executor_agent, verifier_agent = get_agents()
        
        # Step 1: Create plan
        print(f"\n{'='*60}")
        print(f"TASK: {request.task}")
        print(f"{'='*60}")
        
        plan = planner_agent.create_plan(request.task)
        print(f"\nPLAN CREATED:")
        print(f"Steps: {len(plan['steps'])}")
        print(f"Tools needed: {plan['tools_needed']}")
        
        # Step 2: Execute plan
        print(f"\nEXECUTING PLAN...")
        execution_results = executor_agent.execute_plan(plan)
        
        for result in execution_results:
            status = "✓" if result.get("success") else "✗"
            print(f"{status} Step {result['step_number']}: {result['description']}")
        
        # Step 3: Verify and format results
        print(f"\nVERIFYING RESULTS...")
        final_answer = verifier_agent.verify_and_format(
            request.task,
            plan,
            execution_results
        )
        
        execution_time = time.time() - start_time
        
        # Get request metrics
        request_metrics = metrics_tracker.end_request()
        
        print(f"\nCOMPLETED in {execution_time:.2f}s")
        print(f"Tokens used: {request_metrics['total_tokens']}, Cost: ${request_metrics['estimated_cost_usd']:.4f}")
        print(f"{'='*60}\n")
        
        return TaskResponse(
            status="success",
            task=request.task,
            plan=plan,
            execution_results=execution_results,
            final_answer=final_answer,
            execution_time=round(execution_time, 2),
            metrics=MetricsResponse(**request_metrics)
        )
        
    except Exception as e:
        # End metrics tracking even on error
        metrics_tracker.end_request()
        print(f"\nERROR: {str(e)}\n")
        raise HTTPException(
            status_code=500,
            detail=f"Task execution failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║        AI Operations Assistant - Starting Up...          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Check environment variables
    required_vars = {
        "OPENAI_API_KEY": "OpenAI API access",
        "GITHUB_TOKEN": "GitHub API access",
        "OPENWEATHER_API_KEY": "Weather data access"
    }
    
    missing = []
    for var, purpose in required_vars.items():
        if not os.getenv(var):
            missing.append(f"  ✗ {var} - {purpose}")
        else:
            print(f"  ✓ {var} configured")
    
    if missing:
        print("\n⚠️  Warning: Missing environment variables:")
        for msg in missing:
            print(msg)
        print("\nPlease configure your .env file before using the assistant.")
        print("See .env.example for required variables.\n")
    
    print("\n🚀 Starting server on http://localhost:8000")
    print("📖 API docs available at http://localhost:8000/docs")
    print("🏥 Health check at http://localhost:8000/health\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
