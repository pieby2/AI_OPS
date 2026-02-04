"""
Verifier Agent - Validates results and creates final formatted output
"""
from typing import Dict, Any, List
from llm import get_llm_provider


class VerifierAgent:
    """Agent responsible for verifying execution results and formatting final output"""
    
    def __init__(self):
        self.llm = get_llm_provider()
    
    def verify_and_format(
        self, 
        task: str, 
        plan: Dict[str, Any], 
        execution_results: List[Dict[str, Any]]
    ) -> str:
        """
        Verify execution results and create final formatted answer
        
        Args:
            task: Original user task
            plan: Execution plan from PlannerAgent
            execution_results: Results from ExecutorAgent
            
        Returns:
            str: Final formatted answer
        """
        # Check for failures and missing data
        verification = self._verify_completeness(plan, execution_results)
        
        # Format the final answer using LLM
        final_answer = self._format_answer(task, plan, execution_results, verification)
        
        return final_answer
    
    def _verify_completeness(
        self, 
        plan: Dict[str, Any], 
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Verify that all required data was obtained
        
        Returns:
            dict: Verification status with any issues found
        """
        expected_outcome = plan.get("expected_outcome", "")
        total_steps = len(plan.get("steps", []))
        successful_steps = sum(1 for r in results if r.get("success", False))
        failed_steps = [r for r in results if not r.get("success", False)]
        
        return {
            "total_steps": total_steps,
            "successful_steps": successful_steps,
            "failed_steps": failed_steps,
            "expected_outcome": expected_outcome,
            "is_complete": len(failed_steps) == 0
        }
    
    def _format_answer(
        self,
        task: str,
        plan: Dict[str, Any],
        results: List[Dict[str, Any]],
        verification: Dict[str, Any]
    ) -> str:
        """
        Use LLM to format a natural language answer from execution results
        
        Returns:
            str: Formatted final answer
        """
        system_prompt = """You are a result verification agent. Your job is to synthesize execution results into a clear, natural language answer.

Rules:
1. Provide a direct answer to the user's question based on the execution results
2. If some steps failed, acknowledge this and provide partial results if available
3. Format data clearly and concisely
4. Include relevant details like numbers, names, descriptions
5. If no useful data was obtained, explain what went wrong
6. Be conversational but informative
7. Don't include technical details about the execution process unless there were errors

Your response should be a natural language answer, not JSON."""
        
        results_summary = self._summarize_results(results)
        
        user_prompt = f"""Original Task: {task}

Expected Outcome: {verification['expected_outcome']}

Execution Results:
{results_summary}

Verification Status:
- Total Steps: {verification['total_steps']}
- Successful: {verification['successful_steps']}
- Failed: {len(verification['failed_steps'])}

Please provide a clear, natural language answer to the user's task based on these results."""
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            answer = self.llm.chat_completion(messages, temperature=0.5, json_mode=False)
            return answer
            
        except Exception as e:
            # Fallback to basic formatting if LLM fails
            return self._fallback_format(task, results, verification)
    
    def _summarize_results(self, results: List[Dict[str, Any]]) -> str:
        """Create a text summary of execution results"""
        summary_parts = []
        
        for result in results:
            step_num = result.get("step_number")
            description = result.get("description")
            success = result.get("success", False)
            
            summary = f"\nStep {step_num}: {description}"
            summary += f"\nStatus: {'✓ Success' if success else '✗ Failed'}"
            
            if success:
                data = result.get("data", {})
                summary += f"\nData: {str(data)[:500]}"  # Limit data length
            else:
                error = result.get("error", "Unknown error")
                summary += f"\nError: {error}"
            
            summary_parts.append(summary)
        
        return "\n".join(summary_parts)
    
    def _fallback_format(
        self,
        task: str,
        results: List[Dict[str, Any]],
        verification: Dict[str, Any]
    ) -> str:
        """Simple fallback formatting when LLM is unavailable"""
        if not verification['is_complete']:
            failed = verification['failed_steps']
            errors = [f"Step {r['step_number']}: {r.get('error', 'Unknown error')}" for r in failed]
            return f"Unable to complete task. Errors:\n" + "\n".join(errors)
        
        # Extract successful data
        answer_parts = [f"Results for: {task}\n"]
        
        for result in results:
            if result.get("success"):
                data = result.get("data", {})
                answer_parts.append(f"{result['description']}: {data}")
        
        return "\n".join(answer_parts)
