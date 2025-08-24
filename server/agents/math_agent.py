from typing import Dict, List, Optional, Literal
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.errors import GraphRecursionError
from .state import MathAgentState
from .knowledge_base_node import KnowledgeBaseNode
from .websearch_node import WebSearchNode
from .llm_config import gemini_config
import time
import asyncio
import concurrent.futures
import logging

logger = logging.getLogger(__name__)

class MathSolvingAgent:
    
    def __init__(self):
        self.kb_node = KnowledgeBaseNode()
        self.web_node = WebSearchNode()
        self.llm = gemini_config.get_llm()
        self.graph = self._build_graph()
        
        try:
            kb_info = self.kb_node.kb.get_collection_info()
            print(f"Using KB with {kb_info.get('points_count', 0)} problems")
        except Exception as e:
            print(f"KB info error: {e}")
    
    def _route_question(self, state: MathAgentState) -> Dict:
        question = state["question"]
        iteration_count = state.get("iteration_count", 0)
        
        print(f" Routing question (iteration {iteration_count}): {question[:50]}...")
        logger.info(f"Routing question (iteration {iteration_count}): {question}")
        
        new_iteration_count = iteration_count + 1
        
        if iteration_count >= 1:
            route = "web_search"
            routing_msg = AIMessage(content="KB retry failed, using MCP web search")
            print(" Forcing web search due to retry")
            confidence_score = 0.0
        else:
            try:
                print(" Searching knowledge base first...")
                kb_results = self.kb_node.kb.search(question, top_k=3)
                
                if kb_results and kb_results[0]['score'] > 0.2:
                    route = "knowledge_base"
                    confidence_score = kb_results[0]['score']
                    routing_msg = AIMessage(content=f"KB match found (confidence: {confidence_score:.3f})")
                    print(f" Using KB (confidence: {confidence_score:.3f})")
                else:
                    route = "web_search"
                    confidence_score = kb_results[0]['score'] if kb_results else 0
                    routing_msg = AIMessage(content=f"KB confidence too low ({confidence_score:.3f}), using web search")
                    print(f" Using Web Search (KB confidence too low: {confidence_score:.3f})")
            except Exception as e:
                route = "web_search"
                confidence_score = 0.0
                routing_msg = AIMessage(content=f"KB error, using web search: {e}")
                print(f" KB error, using web search: {e}")
        
        print(f" Route decision: {route}")
        logger.info(f"Route decision: {route}")
        
        return {
            "messages": [routing_msg],
            "route_decision": route,
            "route": route,
            "confidence_score": confidence_score,
            "iteration_count": new_iteration_count,
            "kb_results": []
        }
    
    def _solve_with_kb(self, state: MathAgentState) -> Dict:
        print(" Solving with knowledge base...")
        
        try:
            kb_result = self.kb_node.search_and_solve(state)
            
            if kb_result.get("route_decision") == "knowledge_base":
                msg = AIMessage(content="Solution found in Hendrycks MATH dataset")
                kb_result["solution_method"] = "knowledge_base_enhanced"
                kb_result["route"] = "knowledge_base"
                print(f" KB solution with {len(kb_result.get('solution_steps', []))} steps")
            else:
                msg = AIMessage(content="KB search unsuccessful")
                kb_result["confidence_score"] = 0.2
                kb_result["solution_method"] = "knowledge_base_failed"
                kb_result["route"] = "knowledge_base_failed"
            
            kb_result["messages"] = [msg]
            return kb_result
            
        except Exception as e:
            print(f" KB solver error: {e}")
            return {
                "route_decision": "knowledge_base",
                "route": "knowledge_base_error",
                "confidence_score": 0.1,
                "solution_steps": [
                    {"step": 1, "text": "Knowledge base search attempted"},
                    {"step": 2, "text": f"Error encountered: {str(e)[:100]}"}
                ],
                "final_answer": "",
                "errors": [f"KB error: {str(e)}"],
                "solution_method": "knowledge_base_error",
                "messages": [AIMessage(content=f"KB error: {e}")]
            }
    
    def _solve_with_web(self, state: MathAgentState) -> Dict:
        print(" Solving with MCP web search...")
        
        try:
            try:
                loop = asyncio.get_running_loop()
                task = loop.create_task(self.web_node.search_and_solve(state))
                web_result = loop.run_until_complete(task)
            except RuntimeError:
                web_result = asyncio.run(self.web_node.search_and_solve(state))
            
            if web_result and web_result.get("route_decision") == "web_search":
                msg = AIMessage(content="Solution generated from MCP web search")
                web_result["solution_method"] = "mcp_web_search"
                web_result["route"] = "web_search"
                print(f" Web search solution with {len(web_result.get('solution_steps', []))} steps")
            else:
                msg = AIMessage(content="Limited web search results")
                web_result = {
                    "route_decision": "web_search",
                    "route": "web_search",
                    "solution_steps": [
                        {"step": 1, "text": "Searched web sources for mathematical information"},
                        {"step": 2, "text": "Generated solution based on available knowledge"},
                        {"step": 3, "text": "Web search completed with basic results"}
                    ],
                    "final_answer": "Solution generated from web research",
                    "confidence_score": 0.6,
                    "solution_method": "mcp_web_search_fallback"
                }
            
            web_result["messages"] = [msg]
            return web_result
            
        except Exception as e:
            print(f" Web search error: {e}")
            return {
                "route_decision": "web_search",
                "route": "web_search_error",
                "solution_steps": [
                    {"step": 1, "text": "Attempted MCP web search"},
                    {"step": 2, "text": f"Encountered error: {str(e)[:100]}"},
                    {"step": 3, "text": "Please try rephrasing your question"}
                ],
                "final_answer": "Web search encountered difficulties",
                "confidence_score": 0.3,
                "solution_method": "mcp_web_search_error",
                "messages": [AIMessage(content=f"Web search failed: {e}")]
            }
    
    def _build_graph(self) -> CompiledStateGraph:
        workflow = StateGraph(MathAgentState)
        
        workflow.add_node("initializer", self._initialize_state)
        workflow.add_node("router", self._route_question)
        workflow.add_node("kb_solver", self._solve_with_kb)
        workflow.add_node("web_solver", self._solve_with_web)
        workflow.add_node("validator", self._validate_solution)
        workflow.add_node("enhancer", self._enhance_solution)
        workflow.add_node("finalizer", self._finalize_response)
        workflow.add_node("error_handler", self._handle_errors)
        
        workflow.add_edge(START, "initializer")
        workflow.add_edge("initializer", "router")
        
        workflow.add_conditional_edges(
            "router",
            self._routing_condition,
            {
                "knowledge_base": "kb_solver",
                "web_search": "web_solver",
                "error": "error_handler"
            }
        )
        
        workflow.add_edge("kb_solver", "validator")
        workflow.add_edge("web_solver", "validator")
        
        workflow.add_conditional_edges(
            "validator",
            self._validation_condition,
            {
                "good": "enhancer",
                "needs_improvement": "enhancer", 
                "retry": "router"
            }
        )
        
        workflow.add_edge("enhancer", "finalizer")
        workflow.add_edge("error_handler", "finalizer")
        workflow.add_edge("finalizer", END)
        
        return workflow.compile()
    
    def _initialize_state(self, state: MathAgentState) -> Dict:
        return {
            "original_question": state["question"],
            "confidence_threshold": 0.2,
            "max_iterations": 2,
            "iteration_count": 0,
            "retry_count": 0,
            "errors": [],
            "sources": [],
            "processing_time": time.time()
        }
    
    def _validate_solution(self, state: MathAgentState) -> Dict:
        confidence = state.get("confidence_score", 0.0)
        route = state.get("route_decision", "")
        iteration_count = state.get("iteration_count", 0)
        
        if route == "web_search":
            validation_msg = AIMessage(content="Web search result accepted (final fallback)")
            return {
                "validation_result": "good",
                "confidence_score": max(confidence, 0.6),
                "messages": [validation_msg]
            }
        
        if iteration_count >= 2:
            validation_msg = AIMessage(content="Accepting result (max iterations reached)")
            return {
                "validation_result": "good",
                "confidence_score": max(confidence, 0.5),
                "messages": [validation_msg]
            }
        
        if confidence > 0.6:
            validation_msg = AIMessage(content=f"High confidence result: {confidence:.2f}")
            return {
                "validation_result": "good",
                "messages": [validation_msg]
            }
        elif confidence > 0.2:
            validation_msg = AIMessage(content=f"Medium confidence: {confidence:.2f}")
            return {
                "validation_result": "needs_improvement",
                "messages": [validation_msg]
            }
        else:
            validation_msg = AIMessage(content=f"Low confidence: {confidence:.2f}, will retry with web search")
            return {
                "validation_result": "retry",
                "messages": [validation_msg]
            }
    
    def _enhance_solution(self, state: MathAgentState) -> Dict:
        steps = state.get("solution_steps", [])
        confidence = state.get("confidence_score", 0.0)
        method = state.get("solution_method", "unknown")
        route = state.get("route", "unknown")
        
        enhanced_steps = []
        for i, step in enumerate(steps):
            enhanced_steps.append({
                "step": step.get("step", i+1),
                "text": step.get("text", ""),
                "type": step.get("type", "solution_step")
            })
        
        source_info = f"Route: {route} | Method: {method} | Confidence: {confidence:.1%}"
        enhanced_steps.append({
            "step": len(enhanced_steps) + 1,
            "text": source_info,
            "type": "metadata"
        })
        
        return {
            "solution_steps": enhanced_steps,
            "steps": enhanced_steps,
            "route": route,
            "messages": [AIMessage(content="Solution enhanced with routing metadata")]
        }
    
    def _finalize_response(self, state: MathAgentState) -> Dict:
        processing_time = time.time() - state.get("processing_time", time.time())
        
        return {
            "processing_time": processing_time,
            "messages": [AIMessage(content=f"Solution completed in {processing_time:.2f}s")]
        }
    
    def _handle_errors(self, state: MathAgentState) -> Dict:
        errors = state.get("errors", [])
        
        return {
            "solution_steps": [
                {"step": 1, "text": "System encountered an error during processing"},
                {"step": 2, "text": f"Error details: {'; '.join(errors[:2])}"},
                {"step": 3, "text": "Please try rephrasing your question or contact support"}
            ],
            "final_answer": "Unable to provide solution due to system error",
            "confidence_score": 0.1,
            "route_decision": "error_fallback",
            "route": "error",
            "solution_method": "error_handler",
            "messages": [AIMessage(content="Error handled gracefully")]
        }
    
    def _routing_condition(self, state: MathAgentState) -> Literal["knowledge_base", "web_search", "error"]:
        return state.get("route_decision", "knowledge_base")
    
    def _validation_condition(self, state: MathAgentState) -> Literal["good", "needs_improvement", "retry"]:
        validation = self._validate_solution(state)
        return validation.get("validation_result", "good")
    
    async def solve_async(self, question: str) -> Dict:
        print(f" Math Agent solving with KB→MCP fallback: {question[:50]}...")
        
        initial_state = {
            "messages": [HumanMessage(content=question)],
            "question": question,
            "iteration_count": 0,
            "max_iterations": 2,
            "processing_time": time.time()
        }
        
        try:
            result = await self.graph.ainvoke(
                initial_state, 
                config={"recursion_limit": 15}
            )
            
            final_result = {
                "route": result.get("route", result.get("route_decision", "unknown")),
                "route_decision": result.get("route_decision", "unknown"),
                "question": question,
                "steps": result.get("solution_steps", []),
                "solution_steps": result.get("solution_steps", []),
                "final_answer": result.get("final_answer", "No solution generated"),
                "confidence": result.get("confidence_score", 0.0),
                "confidence_score": result.get("confidence_score", 0.0),
                "method": result.get("solution_method", "unknown"),
                "processing_time": result.get("processing_time", 0.0),
                "sources": result.get("sources", []),
                "topic": result.get("topic", "mathematics"),
                "difficulty": result.get("difficulty", "unknown"),
                "enhanced_by": "langgraph_kb_mcp_routing"
            }
            
            print(f" Final result: route={final_result['route']}, confidence={final_result['confidence']:.3f}")
            
            return final_result
            
        except GraphRecursionError as e:
            print(f" Recursion limit exceeded: {e}")
            return {
                "route": "error_recursion",
                "route_decision": "error_recursion",
                "question": question,
                "steps": [
                    {"step": 1, "text": "System reached maximum processing iterations"},
                    {"step": 2, "text": "This may indicate a complex problem requiring manual review"},
                    {"step": 3, "text": "Please try simplifying your question"}
                ],
                "final_answer": "Unable to solve within system limits",
                "confidence": 0.0,
                "error": "Recursion limit exceeded"
            }
        except Exception as e:
            print(f" Async solve error: {e}")
            return {
                "route": "error_general",
                "route_decision": "error_general",
                "question": question,
                "steps": [{"step": 1, "text": f"Async system error: {str(e)}"}],
                "final_answer": "System error occurred",
                "confidence": 0.0,
                "error": str(e)
            }
