import React, { useState, useCallback, useRef } from 'react';
import { solveMathProblem, createStreamConnection } from '../../services/mathAPI';
import { submitFeedback } from '../../services/feedbackAPI';
import ChatInterface from './ChatInterface';

function ConversationalMathTutor() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
  const isProcessing = useRef(false); 

  console.log(' ConversationalMathTutor session ID:', sessionId);

  const sendMessage = useCallback(async (question) => {
    if (!question.trim() || isProcessing.current) return;

    isProcessing.current = true;

    const userMessage = {
      id: `user_${Date.now()}`,
      text: question,
      isUser: true,
      timestamp: new Date(),
      originalQuestion: question
    };

    setMessages(prev => {
      const newMessages = [...prev, userMessage];
      console.log(' Updated messages count:', newMessages.length);
      return newMessages;
    });

    setLoading(true);

    try {
      const conversationHistory = messages.map(msg => ({
        role: msg.isUser ? 'user' : 'assistant',
        content: msg.text,
        request_type: msg.request_type || 'unknown'
      }));

      console.log(' Sending conversation history:', conversationHistory);
      console.log(' Using session ID:', sessionId);

      const aiMessage = {
        id: `ai_${Date.now()}`,
        text: "I'm analyzing your math problem and will solve it step by step...",
        isUser: false,
        timestamp: new Date(),
        streaming_session_id: sessionId, 
        originalQuestion: question,
        showFeedback: true,
        onSolutionComplete: (completedSolution) => {
          console.log(' Solution completed:', completedSolution);
          setMessages(prev => prev.map(msg => 
            msg.id === aiMessage.id 
              ? { 
                  ...msg, 
                  solution: completedSolution,
                  text: completedSolution.conversational_response || 
                        "I've solved your math problem! Here's the solution:",
                  streaming_session_id: null 
                }
              : msg
          ));
          setLoading(false);
          isProcessing.current = false; 
        }
      };

      setMessages(prev => [...prev, aiMessage]);

    } catch (error) {
      console.error(' Send message error:', error);
      const errorMessage = {
        id: `error_${Date.now()}`,
        text: `Error: ${error.message}`,
        isUser: false,
        timestamp: new Date(),
        isError: true,
      };

      setMessages(prev => [...prev, errorMessage]);
      setLoading(false);
      isProcessing.current = false; 
    }
  }, [messages, sessionId]);

  const handleFeedback = useCallback(async (messageId, feedbackData) => {
    try {
      const message = messages.find(m => m.id === messageId);
      if (message && message.solution) {
        await submitFeedback({
          ...feedbackData,
          question: message.solution.question,
          original_solution: message.solution,
          session_id: sessionId 
        });
        setMessages(prev => prev.map(m => 
          m.id === messageId ? { ...m, feedbackSubmitted: true } : m
        ));
      }
    } catch (error) {
      console.error('Feedback submission failed:', error);
    }
  }, [messages, sessionId]);

  return (
    <ChatInterface
      messages={messages}
      loading={loading}
      onSendMessage={sendMessage}
      onFeedback={handleFeedback}
      sessionId={sessionId}
    />
  );
}

export default ConversationalMathTutor;
