import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from dotenv import load_dotenv

load_dotenv()

class GeminiConfig:
    """Configuration for Google Gemini LLM"""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
    
    def get_llm(self, model="gemini-1.5-flash", temperature=0.1):
        """Get configured Gemini LLM"""
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=self.api_key,
            temperature=temperature,
            max_tokens=2048,
            timeout=30
        )
    
    def get_math_solver_prompt(self):
        """Prompt template for math problem solving"""
        return ChatPromptTemplate.from_messages([
            ("system", """You are an expert mathematics tutor. Your task is to solve mathematical problems step by step with clear explanations.

Guidelines:
1. Break down complex problems into simple steps
2. Explain the reasoning behind each step
3. Use clear, educational language
4. Provide the final answer in a clean format
5. If you're unsure, acknowledge limitations

Problem Context: {context}
Confidence Level: {confidence}
"""),
            MessagesPlaceholder(variable_name="messages"),
            ("human", "Please solve this step by step: {question}")
        ])
    
    def get_solution_validator_prompt(self):
        """Prompt template for solution validation"""
        return ChatPromptTemplate.from_messages([
            ("system", """You are a mathematics solution validator. Analyze the given solution for:

1. Mathematical accuracy
2. Logical flow of steps
3. Completeness of explanation
4. Clarity for educational purposes

Rate the solution on a scale of 0.0 to 1.0 and provide specific feedback.

Solution to validate: {solution}
Original question: {question}
"""),
            ("human", "Please validate this solution and provide a confidence score with feedback.")
        ])

# Global instance
gemini_config = GeminiConfig()
