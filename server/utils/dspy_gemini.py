import os
import dspy
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class GeminiDSPyConfig:
    """DSPy configuration with Google Gemini"""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")

        genai.configure(api_key=self.api_key)
        self.initialize_dspy()
    
    def initialize_dspy(self):
        """Initialize DSPy with Gemini model"""
        try:
            self.lm = dspy.LM(
                "gemini/gemini-2.0-flash",
                api_key=self.api_key,
                max_tokens=1024,
                temperature=0.3
            )
            
            dspy.settings.configure(lm=self.lm, max_tokens=1024)
            
            print(" DSPy configured with Gemini 2.0 Flash")
            
        except Exception as e:
            print(f" LiteLLM method failed: {e}")
            
            try:
                self.lm = dspy.LM(
                    model="google/gemini-2.0-flash",
                    api_key=self.api_key,
                    api_base="https://generativelanguage.googleapis.com/v1",
                    max_tokens=1024,
                    temperature=0.3
                )
                
                dspy.settings.configure(lm=self.lm)
                print(" DSPy configured with Gemini (direct API)")
                
            except Exception as e2:
                print(f" Both DSPy-Gemini methods failed: {e2}")
                raise e2
    
    def get_lm(self):
        """Get configured language model"""
        return self.lm
    
    def test_connection(self):
        """Test DSPy-Gemini connection"""
        try:
            test_module = dspy.Predict("question -> answer")
            result = test_module(question="What is 2+2?")
            print(f" DSPy-Gemini test successful: {result.answer}")
            return True
        except Exception as e:
            print(f" DSPy-Gemini test failed: {e}")
            return False

gemini_config = None

def initialize_gemini_dspy():
    """Initialize global Gemini DSPy configuration"""
    global gemini_config
    try:
        gemini_config = GeminiDSPyConfig()
        gemini_config.test_connection()
        return gemini_config
    except Exception as e:
        print(f" Failed to initialize DSPy with Gemini: {e}")
        return None

def get_gemini_lm():
    """Get configured Gemini language model"""
    if gemini_config:
        return gemini_config.get_lm()
    return None
