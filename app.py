import streamlit as st
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from agents import PlannerAgent, ExecutorAgent, VerifierAgent
from metrics import get_metrics_tracker
from cache import get_cache_manager

# Page configuration
st.set_page_config(
    page_title="AI Operations Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Claude Code inspired styling
st.markdown("""
<style>
    /* Claude Code color scheme */
    :root {
        --claude-orange: #D97757;
        --claude-orange-hover: #E8956F;
        --claude-dark: #1a1a1a;
        --claude-darker: #121212;
        --claude-card: #2d2d2d;
        --claude-border: #3d3d3d;
        --claude-text: #e8e8e8;
        --claude-text-muted: #9ca3af;
    }
    
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #D97757 0%, #E8956F 50%, #D97757 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .step-card {
        background-color: #2d2d2d;
        border: 1px solid #3d3d3d;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .success-badge {
        background-color: #22c55e;
        color: #121212;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .error-badge {
        background-color: #ef4444;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
        font-size: 0.8rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #D97757 0%, #C4644A 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #D97757 !important;
        color: #121212 !important;
        border: none !important;
        font-weight: 600 !important;
    }
    
    .stButton > button:hover {
        background-color: #E8956F !important;
    }
    
    /* Input fields */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: #2d2d2d !important;
        border: 1px solid #3d3d3d !important;
        color: #e8e8e8 !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #121212 !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: #e8e8e8;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #2d2d2d !important;
        border: 1px solid #3d3d3d !important;
    }
    
    /* Divider */
    hr {
        border-color: #3d3d3d !important;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_agents():
    """Initialize agents (cached for performance)"""
    return PlannerAgent(), ExecutorAgent(), VerifierAgent()


def execute_task(task: str):
    """Execute a task using the multi-agent system"""
    metrics = get_metrics_tracker()
    metrics.start_request()
    
    start_time = time.time()
    
    try:
        planner, executor, verifier = get_agents()
        
        # Step 1: Planning
        with st.status("🧠 Creating execution plan...", expanded=True) as status:
            plan = planner.create_plan(task)
            st.write(f"**Steps:** {len(plan['steps'])}")
            st.write(f"**Tools needed:** {', '.join(plan['tools_needed'])}")
            status.update(label="✅ Plan created!", state="complete")
        
        # Step 2: Execution
        with st.status("⚙️ Executing steps...", expanded=True) as status:
            execution_results = executor.execute_plan(plan)
            
            for result in execution_results:
                if result.get("success"):
                    st.success(f"Step {result['step_number']}: {result['description']}")
                else:
                    st.error(f"Step {result['step_number']}: {result.get('error', 'Failed')}")
            
            status.update(label="✅ Execution complete!", state="complete")
        
        # Step 3: Verification
        with st.status("🔍 Verifying results...", expanded=True) as status:
            final_answer = verifier.verify_and_format(task, plan, execution_results)
            status.update(label="✅ Verification complete!", state="complete")
        
        execution_time = time.time() - start_time
        request_metrics = metrics.end_request()
        
        return {
            "success": True,
            "plan": plan,
            "execution_results": execution_results,
            "final_answer": final_answer,
            "execution_time": execution_time,
            "metrics": request_metrics
        }
        
    except Exception as e:
        metrics.end_request()
        return {
            "success": False,
            "error": str(e)
        }


def main():
    # Header
    st.markdown('<h1 class="main-header">🤖 AI Operations Assistant</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p style="text-align: center; color: #666;">Multi-agent system for natural language task execution</p>',
        unsafe_allow_html=True
    )
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key Input
        api_key_input = st.text_input(
            "Groq API Key",
            type="password",
            placeholder="gsk_...",
            help="Enter your Groq API key to override the .env file"
        )
        if api_key_input:
            os.environ["GROQ_API_KEY"] = api_key_input
        
        # GitHub Token Input
        github_token_input = st.text_input(
            "GitHub Token",
            type="password",
            placeholder="ghp_...",
            help="Enter your GitHub Personal Access Token"
        )
        if github_token_input:
            os.environ["GITHUB_TOKEN"] = github_token_input
        
        # Tools info
        st.header("🔧 Tools")
        st.subheader("Cache")
        cache = get_cache_manager()
        cache_stats = cache.get_stats()
        st.write(f"Cached entries: {cache_stats['active_entries']}")
        
        if st.button("🗑️ Clear Cache"):
            count = cache.clear()
            st.success(f"Cleared {count} entries")
        
        st.divider()
        
        # Metrics
        st.subheader("📊 Session Metrics")
        metrics = get_metrics_tracker()
        total_metrics = metrics.get_total_metrics()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("LLM Calls", total_metrics['total_calls'])
        with col2:
            st.metric("Total Tokens", total_metrics['total_tokens'])
        
        st.metric("Total Cost", f"${total_metrics['total_cost_usd']:.4f}")
        
        st.divider()
        
        # Tools info
        st.subheader("🔧 Available Tools")
        st.write("- **GitHub**: Search repositories")
        st.write("- **Weather**: Get current weather")
        st.write("- **News**: Search news articles")
    
    # Main content
    st.subheader("💬 Enter Your Task")
    
    # Example tasks
    example_tasks = [
        "What is the weather in Tokyo?",
        "Find popular Python web frameworks on GitHub",
        "Get the latest news about artificial intelligence",
        "What's the weather in London and find AI repositories on GitHub"
    ]
    
    # Quick examples
    st.caption("Quick examples:")
    cols = st.columns(4)
    selected_example = None
    for i, example in enumerate(example_tasks):
        with cols[i]:
            if st.button(f"📝 {example[:25]}...", key=f"example_{i}", use_container_width=True):
                selected_example = example
    
    # Task input
    task_input = st.text_area(
        "Describe what you want to do:",
        value=selected_example if selected_example else "",
        height=100,
        placeholder="e.g., 'What's the weather in Paris and find popular AI repos on GitHub?'"
    )
    
    # Execute button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        execute_button = st.button("🚀 Execute Task", type="primary", use_container_width=True)
    
    # Process task
    if execute_button and task_input:
        st.divider()
        
        # Execute the task
        result = execute_task(task_input)
        
        # Store result in session state to persist after rerun
        st.session_state['last_result'] = result
        st.rerun()
    
    elif execute_button:
        st.warning("Please enter a task to execute.")
    
    # Display last result if available
    if 'last_result' in st.session_state:
        result = st.session_state['last_result']
        
        if result["success"]:
            # Display final answer
            st.subheader("📋 Result")
            st.markdown(result["final_answer"])
            
            # Metrics row
            st.divider()
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("⏱️ Time", f"{result['execution_time']:.2f}s")
            with col2:
                st.metric("🔢 Tokens", result['metrics']['total_tokens'])
            with col3:
                st.metric("💰 Cost", f"${result['metrics']['estimated_cost_usd']:.4f}")
            with col4:
                st.metric("📞 LLM Calls", result['metrics']['llm_calls'])
            
            # Expandable details
            with st.expander("📝 View Execution Details"):
                st.subheader("Plan")
                st.json(result["plan"])
                
                st.subheader("Execution Results")
                for r in result["execution_results"]:
                    status = "✅" if r.get("success") else "❌"
                    st.write(f"{status} **Step {r['step_number']}**: {r['description']}")
                    if r.get("data"):
                        st.json(r["data"])
        else:
            st.error(f"❌ Task failed: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
