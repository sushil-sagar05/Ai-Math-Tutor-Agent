# 🎓 AI Math Tutor - Conversational Learning with Human-in-the-Loop

An advanced AI-powered mathematics tutor that provides step-by-step solutions, educational explanations, and continuous learning through human feedback integration.


## 🚀 Features

- **🤖 Conversational AI Interface**: Natural chat-based math problem solving
- **📊 Real-time Streaming**: Step-by-step solution delivery with live streaming
- **🧠 Smart Routing**: Knowledge base first, web search fallback for comprehensive coverage
- **👨‍🏫 Educational Focus**: Teaching-oriented responses with Socratic questioning
- **🔄 Human-in-the-Loop**: Continuous learning through user feedback
- **🔒 Privacy-First**: Input/output guardrails with secure data handling
- **📱 Responsive Design**: Works seamlessly on desktop and mobile devices

## 🏗️ Architecture Overview

![Architecture Diagram] (https://drive.google.com/file/d/1Uner8rRNZTmh4nieE_vklsewa1os_hgU/view?usp=sharing)

### System Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend** | React/Next.js + Tailwind CSS | Chat interface with streaming UI |
| **Backend** | FastAPI + AsyncIO | API server with real-time streaming |
| **AI Agent** | DSPy + Gemini 2.0 Flash + LangGraph | Core problem-solving intelligence |
| **Knowledge Base** | Qdrant Vector Database | Math problems & solutions storage |
| **Web Search** | MCP + Bing Search API | External knowledge fallback |
| **Feedback System** | PostgreSQL | User feedback & learning data |

## 🔄 Request Flow

sequenceDiagram
participant User
participant Frontend
participant Backend
participant Agent
participant KnowledgeBase
participant WebSearch
participant FeedbackDB
User->>Frontend: Submit math question
Frontend->>Backend: POST /api/solve + context + session_id
Backend->>Agent: Route request with conversation history
Agent->>KnowledgeBase: Query knowledge base
alt KB has solution (confidence > 0.4)
    KnowledgeBase-->>Agent: Return structured solution
else KB confidence low
    Agent->>WebSearch: MCP web search fallback
    WebSearch-->>Agent: Return external resources
end
Agent->>Backend: Stream solution steps (real-time)
Backend->>Frontend: Server-sent events stream
Frontend->>User: Display step-by-step solution
User->>Frontend: Submit feedback (1-5 rating)
Frontend->>Backend: POST /api/feedback
Backend->>FeedbackDB: Store feedback data
FeedbackDB-->>Backend: Confirm storage

## 🛠️ Technology Stack

### Backend
- **FastAPI**: High-performance async web framework
- **DSPy**: Advanced prompt engineering and optimization
- **LangGraph**: AI workflow orchestration
- **Qdrant**: Vector database for semantic search
- **Pydantic**: Data validation and serialization

### Frontend
- **React 18**: Modern UI library with hooks
- **Tailwind CSS**: Utility-first CSS framework
- **ReactMarkdown**: Markdown rendering with KaTeX support
- **Axios**: HTTP client for API communication

### AI & ML
- **Google Gemini 2.0 Flash**: Large language model
- **OpenAI Embeddings**: Text vectorization
- **Hendrycks MATH Dataset**: Training data (12,500+ problems)
- **MCP (Model Context Protocol)**: Web search integration

## 📁 Project Structure

ai-math-tutor/
├── apps/
│ ├── server/ # FastAPI Backend
│ │ ├── agents/ # AI Agent implementation
│ │ ├── api/ # API endpoints
│ │ ├── database/ # Database models & config
│ │ ├── utils/ # Utility functions
│ │ └── main.py # FastAPI application
│ └── web/ # React Frontend
│ ├── src/
│ │ ├── components/ # React components
│ │ ├── services/ # API services
│ │ ├── hooks/ # Custom React hooks
│ │ └── App.js # Main React app
│ └── package.json
├── docs/ # Documentation
├── requirements.txt # Python dependencies
└── README.md

text

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- Git

### 1. Clone Repository
git clone https://github.com/sushil-sagar05/ai-math-tutor-agent.git
cd ai-math-tutor

text

### 2. Backend Setup
cd apps/server
pip install -r requirements.txt

Set environment variables
export GOOGLE_API_KEY="your-gemini-api-key"
export QDRANT_API_KEY=""

Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

text

### 3. Frontend Setup
cd apps/web
npm install
npm run dev

text

### 4. Access Application
- Frontend: http://localhost:3000
- Backend API: http://127.0.0.1:8000


## 🎯 Usage Examples

### Sample Questions (Knowledge Base)
1. **"What is the derivative of sin(x)?"** - Tests basic calculus knowledge
2. **"Solve the quadratic equation x² - 5x + 6 = 0"** - Tests algebraic problem-solving  
3. **"Integrate e^x from 0 to 1"** - Tests definite integration

### Sample Questions (Web Search Fallback)
1. **"Explain the complete proof of the Pythagorean theorem"** - Comprehensive exposition
2. **"What is the sum of the first 100 natural numbers?"** - Formula derivation
3. **"How to compute the Taylor series of cos(x)?"** - Advanced calculus topic

## 🔒 Privacy & Security

- **Input Sanitization**: Removes sensitive information before processing
- **HTTPS Encryption**: Secure data transmission
- **Session Isolation**: Prevents data leakage between users
- **Conversation Anonymization**: Secure storage with session-based IDs
- **Guardrail Middleware**: Validates all API inputs/outputs

## 🤝 Human-in-the-Loop Learning

The system continuously improves through:
- **Real-time Feedback**: 1-5 star ratings with comments
- **Learning Integration**: Feedback influences future responses
- **Prompt Optimization**: DSPy automatically improves prompts
- **Educational Adaptation**: Adjusts to user learning patterns

## 🧪 Testing

### Run Backend Tests
cd apps/server
python -m pytest tests/

text

### Run Frontend Tests
cd apps/web
npm test

text

### API Testing
Use the interactive API documentation at `http://localhost:8000/docs` or test with curl:

curl -X POST "http://127.0.0.1:8000/api/solve"
-H "Content-Type: application/json"
-d '{"question": "What is 2+2?", "session_id": "test_session"}'

text





## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 for Python code
- Use ESLint/Prettier for JavaScript code
- Add tests for new features
- Update documentation as needed



## 🙏 Acknowledgments

- **Hendrycks MATH Dataset**: For comprehensive math problem collection
- **DSPy Framework**: For advanced prompt engineering capabilities
- **Google Gemini**: For powerful language model integration
- **FastAPI Community**: For excellent async web framework
- **React Team**: For modern frontend development tools

## 📧 Contact & Support

- **Author**: Sushil Sagar
- **Email**: sagarsushil1403@gmail.com
-

---

**⭐ If you found this project helpful, please give it a star!**

**🔗 Documentation** https://drive.google.com/file/d/1YOdd_K61lLwlOFZqJzcvn9cd1NSL3lHL/view?usp=sharing




