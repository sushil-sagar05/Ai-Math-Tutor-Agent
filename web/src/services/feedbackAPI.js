import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

const feedbackAPI = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

feedbackAPI.interceptors.request.use((config) => {
  console.log(`[FEEDBACK API] ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

feedbackAPI.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[FEEDBACK API ERROR]:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const submitFeedback = async (feedbackData) => {
  try {
    const response = await feedbackAPI.post('/api/feedback', feedbackData);
    return response.data;
  } catch (error) {
    const errorMessage = error.response?.data?.error || 
                        error.response?.data?.detail || 
                        error.message || 
                        'Failed to submit feedback';
    throw new Error(errorMessage);
  }
};

export const submitFeedbackStream = async (feedbackData, sessionId) => {
  try {
    const response = await feedbackAPI.post(
      `/api/feedback-stream?session_id=${sessionId}`, 
      feedbackData
    );
    return response.data;
  } catch (error) {
    const errorMessage = error.response?.data?.error || 
                        error.response?.data?.detail || 
                        error.message || 
                        'Failed to submit streaming feedback';
    throw new Error(errorMessage);
  }
};

export const getFeedbackStats = async () => {
  try {
    const response = await feedbackAPI.get('/api/learning-stats');
    return response.data;
  } catch (error) {
    throw new Error('Failed to fetch feedback statistics');
  }
};

export const getFeedbackAnalytics = async () => {
  try {
    const response = await feedbackAPI.get('/api/feedback/analytics');
    return response.data;
  } catch (error) {
    throw new Error('Failed to fetch feedback analytics');
  }
};

export default feedbackAPI;
