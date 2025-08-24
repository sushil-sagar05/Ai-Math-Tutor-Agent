import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
import uuid
import os
from dotenv import load_dotenv
from .DataSet_loader import HendrycksMathLoader
import re

load_dotenv()


class MathTextPreprocessor:
    """Enhanced text preprocessing for mathematical content"""
    
    def __init__(self):
        self.math_synonyms = {
            'derivative': ['differentiate', 'differentiation', 'diff', 'slope', 'rate of change'],
            'integral': ['integrate', 'integration', 'area under curve', 'antiderivative'], 
            'equation': ['formula', 'expression', 'relation'],
            'solve': ['find', 'determine', 'calculate', 'compute'],
            'quadratic': ['second degree', 'degree 2', 'x squared', 'parabola'],
            'circle': ['circular', 'round', 'radius', 'diameter', 'circumference'],
            'triangle': ['triangular', 'three sided', 'trigon'],
            'algebra': ['algebraic', 'variables', 'unknowns', 'polynomial'],
            'geometry': ['geometric', 'shapes', 'figures'],
            'calculus': ['differential', 'integral', 'limits'],
            'counting_and_probability': ['chance', 'random', 'statistics'],
            'intermediate_algebra': ['mapping', 'relation', 'f(x)'],
            'number_theory': ['array', 'table', 'linear algebra']
        }
        
        self.latex_mappings = {
            r'\$([^$]+)\$': r'\1',  
            r'\\boxed\{([^}]+)\}': r'\1',  
            r'\\frac\{([^}]+)\}\{([^}]+)\}': r'(\1)/(\2)',  
            r'\^2': ' squared',
            r'\^3': ' cubed', 
            r'\^\{([^}]+)\}': r' to the power of \1',
            r'\\sqrt\{([^}]+)\}': r'square root of \1',
            r'\\sin': 'sine',
            r'\\cos': 'cosine',
            r'\\tan': 'tangent',
            r'\\pi': 'pi',
            r'\\theta': 'theta',
            r'\\alpha': 'alpha',
            r'\\beta': 'beta'
        }
    
    def preprocess_mathematical_text(self, text: str) -> str:
        """Comprehensive preprocessing for mathematical text"""
        if not text:
         return ""

        cleaned = text
        for latex_pattern, replacement in self.latex_mappings.items():
            cleaned = re.sub(latex_pattern, replacement, cleaned)
        cleaned = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', cleaned)
        cleaned = re.sub(r'\\[a-zA-Z]+', '', cleaned)
        cleaned = cleaned.replace('$', '')
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        expanded = cleaned.lower()
        for concept, synonyms in self.math_synonyms.items():
         if concept in expanded:
            synonym_text = ' '.join(synonyms)
            expanded += f" {synonym_text}"
     
        replacements = {
            'find the': 'calculate determine solve',
            'what is': 'find calculate',
            'given that': 'if when',
            'such that': 'where if',
            'let x be': 'variable x unknown x',
            'show that': 'prove demonstrate',
            'prove that': 'show demonstrate verify'
        }
    
        normalized = expanded
        for pattern, replacement in replacements.items():
            normalized = normalized.replace(pattern, f"{pattern} {replacement}")
    
        return normalized


class QuickIngest:
    def __init__(self):
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        
        if qdrant_api_key:
            self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        else:
            try:
                self.client = QdrantClient(url=qdrant_url)
            except:
                print(" Using in-memory Qdrant for development")
                self.client = QdrantClient(":memory:")
        
        self.collection_name = "math_kb"
        self.loader = HendrycksMathLoader()
        self.vectorizer = TfidfVectorizer(max_features=384, stop_words='english')
        self.preprocessor = MathTextPreprocessor()  
        
    def create_collection(self):
        """Create or recreate Qdrant collection"""
        try:
            self.client.delete_collection(self.collection_name)
            print(f" Deleted existing collection: {self.collection_name}")
        except:
            pass 
        
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        print(f" Created collection: {self.collection_name}")
        
    def ingest(self, limit=500):
        """Enhanced ingestion with dynamic vector sizing"""
        print(" Starting Qdrant ingestion with dynamic vector size...")
    

        problems = self.loader.load_problems(limit=limit)
        if not problems:
            print(" No problems loaded!")
            return []
    
        print(f"Loaded {len(problems)} problems")
        documents = []
        questions = []
    
        for problem in problems:
            original_question = problem.get('question', '')
            enhanced_text = self.preprocessor.preprocess_mathematical_text(original_question)
            full_searchable_text = f"{enhanced_text} {original_question}"
        
            questions.append(original_question)
            documents.append(full_searchable_text)

        vectors = self.vectorizer.fit_transform(documents).toarray()
        vectors_dim = vectors.shape[1]  
    
        print(f" Generated {len(vectors)} TF-IDF vectors with dimension {vectors_dim}")

        try:
            self.client.delete_collection(self.collection_name)
            print(f" Deleted existing collection: {self.collection_name}")
        except:
            pass  
    
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vectors_dim, distance=Distance.COSINE)
        )
        print(f" Created collection: {self.collection_name} with vector size {vectors_dim}")
        points = []
        for i, (problem, vector) in enumerate(zip(problems, vectors)):
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector.tolist(),
                    payload={
                    "question": problem["question"],
                    "topic": problem.get("topic", "mathematics"),
                    "difficulty": problem.get("difficulty", "unknown"),
                    "final_answer": problem.get("final_answer", ""),
                    "solution_steps": problem.get("solution_steps", []),
                    "full_solution": problem.get("full_solution", ""),
                    "subject": problem.get("subject", "math"),
                    "keywords": problem.get("keywords", [])
                }
            )
        )

        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(collection_name=self.collection_name, points=batch)
            print(f" Ingested batch {i//batch_size + 1}/{(len(points) + batch_size - 1)//batch_size}")
    
        print(f" Successfully ingested {len(points)} problems with dynamic vector size!")
    

        vectorizer_path = Path("data/vectorizer.pkl")
        vectorizer_path.parent.mkdir(exist_ok=True)
        import pickle
        with open(vectorizer_path, 'wb') as f:
            pickle.dump(self.vectorizer, f)
    
        return questions[:5]

    def search(self, query, top_k=3):
        """Enhanced search with mathematical preprocessing"""
        try:
            vectorizer_path = Path("data/vectorizer.pkl")
            if vectorizer_path.exists():
                import pickle
                with open(vectorizer_path, 'rb') as f:
                    vectorizer = pickle.load(f)
            else:
                print(" Vectorizer not found, using current one")
                vectorizer = self.vectorizer
            enhanced_query = self.preprocessor.preprocess_mathematical_text(query)
            combined_query = f"{enhanced_query} {query}"
            query_vector = vectorizer.transform([combined_query]).toarray()[0].tolist()

            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=0.05  
            )
            
            print(f" Debug: Found {len(search_results)} results")
            if search_results:
                print(f" Debug: First result type: {type(search_results[0])}")
            results = []
            for result in search_results:
                try:
                    if hasattr(result, 'payload') and hasattr(result, 'score') and hasattr(result, 'id'):
                        payload = result.payload
                        score = float(result.score)
                        result_id = result.id
                    elif isinstance(result, dict):
                        payload = result.get('payload', {})
                        score = float(result.get('score', 0))
                        result_id = result.get('id', 'unknown')
                    elif hasattr(result, '__dict__'):
                        result_dict = result.__dict__
                        payload = result_dict.get('payload', {})
                        score = float(result_dict.get('score', 0))
                        result_id = result_dict.get('id', 'unknown')
                        
                    else:
                        print(f" Unknown result format: {type(result)}")
                        payload = {
                            'question': 'Unable to parse question',
                            'topic': 'unknown',
                            'final_answer': 'Unable to parse answer'
                        }
                        score = 0.1
                        result_id = 'unknown'
                    
                    print(f" Debug: Payload extracted: {type(payload)}")
                    
                    results.append({
                        'problem': payload,
                        'score': score,
                        'id': result_id
                    })
                    
                except Exception as item_error:
                    print(f" Error processing individual result: {item_error}")
                    results.append({
                        'problem': {
                            'question': f'Error parsing result: {str(item_error)[:50]}',
                            'topic': 'error',
                            'final_answer': 'Unable to retrieve answer'
                        },
                        'score': 0.1,
                        'id': 'error'
                    })
            
            print(f" Debug: Returning {len(results)} formatted results")
            return results
            
        except Exception as e:
            print(f" Search error details: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def multi_strategy_search(self, query: str, top_k: int = 5) -> list:
        """Multi-strategy search for maximum coverage"""
        all_results = []
        
        enhanced_results = self.search(query, top_k)
        all_results.extend(enhanced_results)
        
        original_results = self.search_original(query, top_k)
        all_results.extend(original_results)
        
        concept_results = self.concept_search(query, top_k)
        all_results.extend(concept_results)
        
        seen_ids = set()
        unique_results = []
        
        for result in all_results:
            result_id = result.get('id', 'unknown')
            if result_id not in seen_ids:
                seen_ids.add(result_id)
                unique_results.append(result)
        
        unique_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return unique_results[:top_k]
    
    def search_original(self, query: str, top_k: int) -> list:
        """Search without preprocessing for comparison"""
        try:
            vectorizer_path = Path("data/vectorizer.pkl")
            if vectorizer_path.exists():
                import pickle
                with open(vectorizer_path, 'rb') as f:
                    vectorizer = pickle.load(f)
            else:
                vectorizer = self.vectorizer
            
            query_vector = vectorizer.transform([query]).toarray()[0].tolist()
            
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=0.05
            )
            
            results = []
            for result in search_results:
                if hasattr(result, 'payload'):
                    results.append({
                        'problem': result.payload,
                        'score': float(result.score),
                        'id': result.id
                    })
            
            return results
            
        except Exception as e:
            print(f" Original search failed: {e}")
            return []
    
    def concept_search(self, query: str, top_k: int) -> list:
        """Concept-based search using mathematical domain knowledge"""
        concept_queries = []
        query_lower = query.lower()
        
        concept_mappings = {
            'derivative': 'calculus differentiation slope tangent rate change',
            'integral': 'calculus integration area antiderivative',
            'quadratic': 'algebra second degree polynomial parabola',
            'circle': 'geometry radius diameter circumference area',
            'triangle': 'geometry trigonometry angles sides',
            'probability': 'statistics chance random event',
            'matrix': 'linear algebra vectors transformation'
        }
        
        for concept, expanded_terms in concept_mappings.items():
            if concept in query_lower:
                concept_queries.append(expanded_terms)
        
        if concept_queries:
            expanded_query = ' '.join(concept_queries)
            return self.search_original(expanded_query, top_k)
        
        return []
    
    def get_collection_info(self):
        """Get information about the collection"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "status": "active",
                "points_count": info.points_count,
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    ingest = QuickIngest()

    print(" Testing enhanced ingestion with NLP preprocessing...")
    samples = ingest.ingest(limit=50)  
    

    if samples:
        print("\n🔍 Testing enhanced search...")
        test_queries = [
            "derivative sin cos",  
            "algebra quadratic",   
            "solve quadratic equation x^2 + 5x + 6 = 0",
            "find the area of a circle with radius 5",
            "calculate derivative of x^3",
            "geometry triangle angles",
            "probability random events"
        ]
        
        for query in test_queries:
            print(f"\n Testing query: '{query}'")
            results = ingest.search(query)
            print(f"Found {len(results)} results:")
            for i, r in enumerate(results, 1):
                question = r['problem'].get('question', 'N/A')[:60]
                topic = r['problem'].get('topic', 'N/A')
                score = r['score']
                print(f"  {i}. Score: {score:.3f} | Topic: {topic}")
                print(f"      Question: {question}...")

        info = ingest.get_collection_info()
        print(f"\n Collection info: {info}")
    else:
        print(" No samples loaded, skipping search test")
