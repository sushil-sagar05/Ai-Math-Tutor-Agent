import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

const mathAPI = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000,
});

mathAPI.interceptors.request.use((config) => {
  console.log(`[MATH API] ${config.method?.toUpperCase()} ${config.url}`);
  if (config.data) {
    console.log('[MATH API] Request data:', config.data);
  }
  return config;
});

mathAPI.interceptors.response.use(
  (response) => {
    console.log(`[MATH API] Response:`, response.data);
    return response;
  },
  (error) => {
    console.error('[MATH API ERROR]:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const solveMathProblem = async (payload) => {
  try {
    const requestData = typeof payload === 'string' 
      ? { 
          question: payload, 
          session_id: `session_${Date.now()}`,
          conversation_history: []
        }
      : {
          question: payload.question,
          session_id: payload.session_id || `session_${Date.now()}`,
          conversation_history: payload.conversation_history || []
        };

    console.log(' Sending request with:', requestData);

    const response = await mathAPI.post('/api/solve', requestData);
    
    if (response.headers['content-type']?.includes('text/event-stream')) {
      return {
        isStreaming: true,
        session_id: requestData.session_id,
        response: response
      };
    }
    
    return response.data;
  } catch (error) {
    const errorMessage = error.response?.data?.error || 
                        error.response?.data?.detail || 
                        error.message || 
                        'Failed to solve problem';
    throw new Error(errorMessage);
  }
};

export const createStreamConnection = async (question, sessionId, callbacks = {}, conversationHistory = []) => {
  try {
    console.log(' Creating stream connection:', { 
      question: question?.substring(0, 50) + '...', 
      sessionId, 
      historyLength: conversationHistory.length 
    });
    const requestBody = {
      question,
      session_id: sessionId,
      conversation_history: conversationHistory 
    };

    console.log(' Stream request body:', requestBody);
    
    const response = await fetch(`${API_BASE_URL}/api/solve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    const processStream = async () => {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            console.log('🔚 Stream ended');
            break;
          }

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                console.log(' Stream event:', data.type, data);
                handleStreamEvent(data, callbacks);
              } catch (parseError) {
                console.error(' Error parsing stream data:', parseError);
              }
            }
          }
        }
      } catch (streamError) {
        console.error(' Stream processing error:', streamError);
        callbacks.onError?.({ message: streamError.message });
      }
    };

    processStream();

    return () => {
      console.log(' Cleaning up stream connection');
      reader.cancel();
    };

  } catch (error) {
    console.error(' Stream connection error:', error);
    callbacks.onConnectionError?.(error);
    throw error;
  }
};

const handleStreamEvent = (data, callbacks) => {
  console.log(' Handling event:', data.type);
  
  switch (data.type) {
    case 'connected':
      console.log(' Stream connected');
      callbacks.onConnect?.(data);
      break;
    case 'processing_started':
      console.log(' Processing started');
      callbacks.onProcessingStart?.(data);
      break;
    case 'routing':
      console.log(' Routing');
      callbacks.onRouting?.(data);
      break;
    case 'routing_result':
      console.log(' Routing result');
      callbacks.onRoutingResult?.(data);
      break;
    case 'step_update':
      console.log(' Step update');
      callbacks.onStepUpdate?.(data);
      break;
    case 'step_generated':
      console.log(' Step generated');
      callbacks.onStepGenerated?.(data);
      break;
    case 'solution_complete':
      console.log(' Solution complete');
      callbacks.onSolutionComplete?.(data);
      break;
    case 'completion':
      console.log(' Completion');
      callbacks.onCompletion?.(data);
      break;
    case 'error':
      console.error(' Stream error');
      callbacks.onError?.(data);
      break;
    default:
      console.log(' Unknown event:', data.type);
      callbacks.onUnknownEvent?.(data);
  }
};

export const checkSystemHealth = async () => {
  try {
    const response = await mathAPI.get('/api/health');
    return response.data;
  } catch (error) {
    throw new Error('System health check failed');
  }
};

export const getLearningStats = async () => {
  try {
    const response = await mathAPI.get('/api/learning-stats');
    return response.data;
  } catch (error) {
    throw new Error('Failed to fetch learning statistics');
  }
};

export const getConversationalStats = async () => {
  try {
    const response = await mathAPI.get('/api/conversational-stats');
    return response.data;
  } catch (error) {
    throw new Error('Failed to fetch conversational statistics');
  }
};

export const getSystemStatus = async () => {
  try {
    const response = await mathAPI.get('/api/system-status');
    return response.data;
  } catch (error) {
    throw new Error('Failed to fetch system status');
  }
};

export default mathAPI;
