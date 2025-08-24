import json
import os
from pathlib import Path
from typing import List, Dict, Any
import re

class HendrycksMathLoader:
    def __init__(self, data_path: str = "data/Math_Dataset"):
        self.data_dir = Path(data_path)
        
    def load_problems(self, subset: str = "train", limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Load problems from extracted ZIP contents
        Args:
            subset: "train" or "test"
            limit: Max problems to load
        """
        print(f" Loading Hendrycks MATH from {self.data_dir}")
        
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {self.data_dir}")
        
        problems = []
        loaded_count = 0
        subset_dir = self.data_dir / subset
        if not subset_dir.exists():
            json_files = list(self.data_dir.rglob("*.json"))
        else:
            json_files = list(subset_dir.glob("*.json"))
        
        if not json_files:
            raise FileNotFoundError(f"No JSON files found in {self.data_dir}")
        
        print(f" Found {len(json_files)} files to process")
        
        for json_file in json_files:
            if loaded_count >= limit:
                break
                
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = [data] 
                else:
                    continue
                
                subject = json_file.stem  
                
                for i, item in enumerate(items):
                    if loaded_count >= limit:
                        break
                    
                    problem = self.parse_problem(item, subject, i)
                    if problem:
                        problems.append(problem)
                        loaded_count += 1
                        
            except Exception as e:
                print(f"  Error reading {json_file}: {e}")
                continue
        
        print(f" Loaded {len(problems)} problems")
        return problems
    
    def parse_problem(self, item: Dict, subject: str, index: int) -> Dict[str, Any]:
        """Parse individual problem"""
        try:
            question = item.get('problem', item.get('question', ''))
            solution = item.get('solution', '')
            level = item.get('level', 'unknown')
            problem_type = item.get('type', subject)
            
            if not question:
                return None

            final_answer = self.extract_boxed_answer(solution)

            steps = self.solution_to_steps(solution)
            
            return {
                "id": f"hendrycks_{subject}_{index:04d}",
                "question": question.strip(),
                "topic": problem_type.lower().replace(' ', '_'),
                "difficulty": str(level).replace('Level ', ''),
                "solution_steps": steps,
                "final_answer": final_answer,
                "full_solution": solution,
                "subject": subject,
                "keywords": self.extract_keywords(question, problem_type)
            }
            
        except Exception as e:
            print(f"Error parsing problem: {e}")
            return None
    
    def extract_boxed_answer(self, solution: str) -> str:
        """Extract answer from \\boxed{} notation"""
        boxed_pattern = r'\\boxed\{([^}]+)\}'
        matches = re.findall(boxed_pattern, solution)
        return matches[-1] if matches else "No answer found"
    
    def solution_to_steps(self, solution: str) -> List[Dict]:
        """Convert solution to step format"""
        sentences = solution.split('. ')
        steps = []
        for i, sentence in enumerate(sentences[:8], 1):  
            if len(sentence.strip()) > 10:
                steps.append({
                    "step": i,
                    "text": sentence.strip()
                })
        return steps
    
    def extract_keywords(self, question: str, topic: str) -> List[str]:
        """Extract math keywords"""
        keywords = [topic.lower()]
        math_terms = ['solve', 'find', 'calculate', 'prove', 'equation', 'function']
        
        for term in math_terms:
            if term in question.lower():
                keywords.append(term)
        
        return list(set(keywords))

if __name__ == "__main__":
    loader = HendrycksMathLoader()
    
    try:
        problems = loader.load_problems(limit=5)
        print("\n Sample Problems:")
        for p in problems[:2]:
            print(f"Question: {p['question'][:80]}...")
            print(f"Topic: {p['topic']}")
            print(f"Answer: {p['final_answer']}")
            print("-" * 40)
    except FileNotFoundError as e:
        print(f" {e}")
        print("Please extract the ZIP file to: apps/server/data/hendrycks_math/")
