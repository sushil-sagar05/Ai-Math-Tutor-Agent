from typing import Dict
from .state import MathAgentState
from .llm_config import gemini_config
from Knowledge_Base.ingest import QuickIngest
import re

class KnowledgeBaseNode:

    def __init__(self):
        self.kb = QuickIngest()
        self.llm = gemini_config.get_llm()
        
    def search_and_solve(self, state: MathAgentState) -> Dict:
        question = state["question"]
        print(f"KB searching for: {question}")

        try:
            kb_results = self.kb.search(question, top_k=3)
            
            if not kb_results:
                return self._no_match_response(question)
                
            best_result = kb_results[0]
            confidence = best_result.get("score", 0.0)
            best_problem = best_result.get("problem", {})
            
            if confidence < 0.3:
                return self._no_match_response(question)

            enhanced_solution = self._generate_enhanced_steps(question, best_problem)

            return {
                "route_decision": "knowledge_base",
                "solution_steps": enhanced_solution["steps"],
                "final_answer": enhanced_solution["final_answer"],
                "confidence_score": confidence,
                "solution_method": "knowledge_base_enhanced_steps",
                "sources": [{"title": "Hendrycks MATH Dataset", "type": "knowledge_base"}],
                "topic": best_problem.get("topic", "mathematics"),
                "difficulty": best_problem.get("difficulty", "unknown"),
                "kb_info": f"KB similarity: {confidence:.2f}"
            }

        except Exception as e:
            return self._error_response(question, str(e))

    def _generate_enhanced_steps(self, question: str, kb_problem: Dict) -> Dict:
        
        raw_solution = kb_problem.get('solution_steps', [])
        original_answer = kb_problem.get('final_answer', '')
        kb_question = kb_problem.get('question', '')
        
        if isinstance(raw_solution, list):
            solution_text = ' '.join([str(step) for step in raw_solution])
        else:
            solution_text = str(raw_solution)
            
        cleaned_solution = self._clean_latex_solution(solution_text)
        cleaned_answer = self._clean_latex_solution(original_answer)
        
        enhanced_prompt = f"""You are a math tutor. Break down the solution into clear, numbered steps.

Student Question: {question}
Reference Problem: {kb_question}
Reference Solution: {cleaned_solution[:400]}

Create exactly 4-6 numbered steps. Each step should be one clear mathematical operation or concept.

Format EXACTLY like this:
Step 1: [First action - what to do and why]
Step 2: [Second action - show the calculation]  
Step 3: [Third action - combine or simplify]
Step 4: [Fourth action - state the result]

Make each step complete but concise. End with the final numerical answer.
"""

        try:
            response = self.llm.invoke(enhanced_prompt)
            steps = self._parse_steps_reliably(response.content)
            final_answer = self._extract_final_answer(response.content, cleaned_answer)
            
            return {
                "steps": steps,
                "final_answer": final_answer
            }
            
        except Exception as e:
            return self._fallback_steps_solution(question, cleaned_answer)

    def _parse_steps_reliably(self, content: str) -> list:
        steps = []
        
        step_patterns = [
            r'Step\s+(\d+):\s*(.*?)(?=Step\s+\d+:|$)',
            r'(\d+)\.\s+(.*?)(?=\d+\.|$)',
            r'(\d+)\)\s+(.*?)(?=\d+\)|$)'
        ]
        
        for pattern in step_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            if matches and len(matches) >= 2:
                for i, (num, text) in enumerate(matches):
                    clean_text = text.strip()
                    clean_text = re.sub(r'\n+', ' ', clean_text)
                    clean_text = re.sub(r'\s+', ' ', clean_text)
                    
                    if len(clean_text) > 5:
                        steps.append({
                            "step": int(num) if num.isdigit() else i + 1,
                            "text": clean_text[:300],
                            "type": "solution_step"
                        })
                break
        
        if not steps:
            sentences = [s.strip() for s in content.split('.') if len(s.strip()) > 20]
            for i, sentence in enumerate(sentences[:5]):
                if sentence:
                    steps.append({
                        "step": i + 1,
                        "text": f"Apply mathematical reasoning: {sentence}",
                        "type": "solution_step"
                    })
        
        if not steps:
            steps = [
                {"step": 1, "text": "Analyze the given mathematical problem", "type": "solution_step"},
                {"step": 2, "text": "Apply appropriate mathematical techniques", "type": "solution_step"},
                {"step": 3, "text": "Calculate the result step by step", "type": "solution_step"},
                {"step": 4, "text": "Verify and state the final answer", "type": "solution_step"}
            ]
        
        return steps

    def _extract_final_answer(self, content: str, fallback_answer: str) -> str:
        patterns = [
            r"final answer[:\s]*([^\n.]+)",
            r"answer[:\s]*([^\n.]+)",
            r"result[:\s]*([^\n.]+)",
            r"therefore[:\s]*([^\n.]+)",
            r"(\d+\s*treeks?)",
            r"([a-zA-Z0-9\s\+\-\*\^\(\)]+\s*=\s*[a-zA-Z0-9\s\+\-\*\^\(\)]+)"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                clean_match = self._clean_latex_solution(match.strip())
                if clean_match and len(clean_match) > 1:
                    return clean_match
        
        if fallback_answer:
            return self._clean_latex_solution(fallback_answer)
        
        return "See solution steps above"

    def _clean_latex_solution(self, solution_text: str) -> str:
        if not solution_text:
            return ""
            
        cleaned = re.sub(r'\\begin\{.*?\}.*?\\end\{.*?\}', '', solution_text, flags=re.DOTALL)
        cleaned = re.sub(r'\\boxed\{([^}]+)\}', r'\1', cleaned)
        cleaned = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', cleaned)
        cleaned = re.sub(r'\\[a-zA-Z]+', '', cleaned)
        cleaned = re.sub(r'\$([^$]*)\$', r'\1', cleaned)
        cleaned = cleaned.replace('$', '')
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = re.sub(r'&=', '=', cleaned)
        cleaned = re.sub(r'\\\\', ' ', cleaned)
        
        return cleaned

    def _fallback_steps_solution(self, question: str, answer: str) -> Dict:
        if "expand" in question.lower():
            steps = [
                {"step": 1, "text": "Identify the expression to expand using distributive property", "type": "solution_step"},
                {"step": 2, "text": "Multiply each term in the first bracket by each term in the second bracket", "type": "solution_step"},
                {"step": 3, "text": "Combine like terms by adding coefficients of the same variables", "type": "solution_step"},
                {"step": 4, "text": "Write the final expanded form in standard polynomial notation", "type": "solution_step"}
            ]
        elif "solve" in question.lower():
            steps = [
                {"step": 1, "text": "Set up the equation by identifying known and unknown variables", "type": "solution_step"},
                {"step": 2, "text": "Apply algebraic operations to isolate the variable", "type": "solution_step"},
                {"step": 3, "text": "Perform calculations to find the numerical value", "type": "solution_step"},
                {"step": 4, "text": "Verify the solution by substituting back into original equation", "type": "solution_step"}
            ]
        else:
            steps = [
                {"step": 1, "text": "Analyze the mathematical problem and identify the approach needed", "type": "solution_step"},
                {"step": 2, "text": "Apply relevant mathematical concepts and formulas", "type": "solution_step"},
                {"step": 3, "text": "Execute calculations systematically to reach the solution", "type": "solution_step"},
                {"step": 4, "text": "State the final answer clearly", "type": "solution_step"}
            ]
        
        return {
            "steps": steps,
            "final_answer": answer or "Solution completed following the steps above"
        }

    def _no_match_response(self, question: str) -> Dict:
        return {
            "route_decision": "knowledge_base",
            "confidence_score": 0.1,
            "solution_steps": [{
                "step": 1,
                "text": "No similar problems found in knowledge base - routing to web search",
                "type": "solution_step"
            }],
            "final_answer": "",
            "solution_method": "knowledge_base_no_match"
        }

    def _error_response(self, question: str, error_msg: str) -> Dict:
        return {
            "route_decision": "knowledge_base",
            "confidence_score": 0.0,
            "solution_steps": [{
                "step": 1,
                "text": f"Knowledge base search encountered an error: {error_msg[:100]}",
                "type": "solution_step"
            }],
            "final_answer": "Error accessing knowledge base",
            "solution_method": "knowledge_base_error"
        }
