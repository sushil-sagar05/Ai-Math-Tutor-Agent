import React, { useState, useRef, useCallback, useEffect } from 'react';
import MessageBubble from './MessageBubble';
import WelcomeScreen from './WelcomeScreen';
import ChatInput from './ChatInput';
import { useScrollToElement } from '../../hooks/UseScrollToElement';
import { createStreamConnection } from '../../services/mathAPI';
import { submitFeedback } from '../../services/feedbackAPI';

function ChatInterface({ 
  messages: externalMessages, 
  loading: externalLoading, 
  onSendMessage: externalOnSendMessage, 
  onFeedback: externalOnFeedback,
  sessionId: externalSessionId 
}) {
  const [input, setInput] = useState('');
  const [internalMessages, setInternalMessages] = useState([]);
  const [internalLoading, setInternalLoading] = useState(false);
  const [currentStreamSession, setCurrentStreamSession] = useState(null);
  
  const [internalSessionId] = useState(() => 
    externalSessionId || `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  );
  
  const messagesEndRef = useRef(null);
  const solutionRef = useRef(null);
  const streamCleanupRef = useRef(null);

  const messages = externalMessages || internalMessages;
  const loading = externalLoading !== undefined ? externalLoading : internalLoading;
  const sessionId = externalSessionId || internalSessionId;

  console.log(' ChatInterface render:', {
    messagesCount: messages.length,
    loading,
    sessionId,
    currentStreamSession
  });

  useScrollToElement(messagesEndRef, messages);
  useScrollToElement(solutionRef, messages, {
    condition: (messages) => {
      const lastMessage = messages[messages.length - 1];
      return lastMessage && !lastMessage.isUser && (lastMessage.solution || lastMessage.streaming_session_id);
    },
    delay: 400,
    options: { behavior: 'smooth', block: 'center' }
  });

  useEffect(() => {
    return () => {
      if (streamCleanupRef.current) {
        console.log('🧹 Cleaning up stream on unmount');
        streamCleanupRef.current();
      }
    };
  }, []);

  const buildConversationHistory = useCallback((currentMessages) => {
    return currentMessages
      .filter(msg => msg.text && msg.text.trim()) 
      .map(msg => ({
        role: msg.isUser ? 'user' : 'assistant',
        content: msg.text,
        request_type: msg.request_type || 'unknown'
      }));
  }, []);

  const handleInternalSendMessage = useCallback(async (question) => {
    const safeQuestion = (question || '').trim();
    if (!safeQuestion) return;

    const userMessage = {
      id: `user_${Date.now()}`,
      text: safeQuestion,
      isUser: true,
      timestamp: new Date(),
      originalQuestion: safeQuestion
    };

    const conversationHistory = buildConversationHistory(internalMessages);

    console.log(' Sending message with context:', {
      question: safeQuestion,
      sessionId,
      historyLength: conversationHistory.length
    });

    setInternalMessages(prev => [...prev, userMessage]);
    setInternalLoading(true);
    setCurrentStreamSession(sessionId); 

    try {
      const aiMessage = {
        id: `ai_${Date.now()}`,
        text: "I'm analyzing your math problem and will solve it step by step...",
        isUser: false,
        timestamp: new Date(),
        streaming_session_id: sessionId, 
        originalQuestion: safeQuestion,
        showFeedback: true,
        conversationHistory: conversationHistory, 
        onSolutionComplete: (completedSolution) => {
          console.log(' Solution completed for message:', aiMessage.id);
          setInternalMessages(prev => prev.map(msg => 
            msg.id === aiMessage.id 
              ? { 
                  ...msg, 
                  solution: completedSolution,
                  text: completedSolution.conversational_response || 
                        "I've solved your math problem! Here's the step-by-step solution:",
                  streaming_session_id: null
                }
              : msg
          ));
          setInternalLoading(false);
          setCurrentStreamSession(null);
        }
      };

      setInternalMessages(prev => [...prev, aiMessage]);

      if (streamCleanupRef.current) {
        streamCleanupRef.current();
      }
      streamCleanupRef.current = await createStreamConnection(
        safeQuestion,
        sessionId, 
        {
          onConnect: (data) => {
            console.log(' Stream connected:', data);
          },
          onProcessingStart: (data) => {
            setInternalMessages(prev => prev.map(msg => 
              msg.id === aiMessage.id 
                ? { ...msg, text: data.message || "Starting to process your question..." }
                : msg
            ));
          },
          onRoutingResult: (data) => {
            setInternalMessages(prev => prev.map(msg => 
              msg.id === aiMessage.id 
                ? { 
                    ...msg, 
                    text: `Great! I found a ${data.route === 'knowledge_base' ? 'similar problem in my knowledge base' : 'solution through web search'} with ${(data.confidence * 100).toFixed(1)}% confidence.`
                  }
                : msg
            ));
          },
          onStepGenerated: (data) => {
            console.log(' Step generated:', data);
          },
          onSolutionComplete: (data) => {
            aiMessage.onSolutionComplete(data.data);
          },
          onError: (data) => {
            setInternalMessages(prev => prev.map(msg => 
              msg.id === aiMessage.id 
                ? { 
                    ...msg, 
                    text: `Sorry, I encountered an error: ${data.message}`,
                    isError: true
                  }
                : msg
            ));
            setInternalLoading(false);
            setCurrentStreamSession(null);
          },
          onConnectionError: (error) => {
            console.error(' Stream connection error:', error);
            setInternalLoading(false);
            setCurrentStreamSession(null);
          }
        },
        conversationHistory 
      );

    } catch (error) {
      console.error(' Error starting streaming solve:', error);
      
      const errorMessage = {
        id: `error_${Date.now()}`,
        text: `I apologize, but I encountered an error while trying to solve your problem: ${error.message}. Please try again or rephrase your question.`,
        isUser: false,
        isError: true,
        timestamp: new Date()
      };
      
      setInternalMessages(prev => [...prev, errorMessage]);
      setInternalLoading(false);
      setCurrentStreamSession(null);
    }
  }, [internalMessages, sessionId, buildConversationHistory]);

  const handleInternalFeedback = useCallback(async (messageId, feedbackData) => {
    const message = messages.find(m => m.id === messageId);
    
    try {
      await submitFeedback({
        ...feedbackData,
        question: message.originalQuestion,
        original_solution: message.solution,
        session_id: sessionId 
      });

      setInternalMessages(prev => prev.map(msg => 
        msg.id === messageId 
          ? { 
              ...msg, 
              feedbackSubmitted: true, 
              feedbackDetails: {
                rating: feedbackData.user_rating,
                improvement_triggered: feedbackData.user_rating <= 2
              }
            }
          : msg
      ));

    } catch (error) {
      console.error(' Error submitting feedback:', error);
    }
  }, [messages, sessionId]);

  const handleSendMessage = useCallback((message) => {
    if (externalOnSendMessage) {
      externalOnSendMessage(message);
    } else {
      handleInternalSendMessage(message);
    }
    setInput('');
  }, [externalOnSendMessage, handleInternalSendMessage]);

  const handleFeedback = useCallback((messageId, feedbackData) => {
    if (externalOnFeedback) {
      externalOnFeedback(messageId, feedbackData);
    } else {
      handleInternalFeedback(messageId, feedbackData);
    }
  }, [externalOnFeedback, handleInternalFeedback]);

  const conversationHistory = buildConversationHistory(messages);

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <header className="bg-white border-b p-4 shadow-sm">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-xl font-bold text-gray-800 flex items-center">
            <span className="text-2xl mr-2">🎓</span>
            <span>AI Math Tutor</span>
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            Conversational learning with human feedback & real-time streaming
          </p>
          <div className="flex gap-2 mt-2">
            <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs">
              Conversational
            </span>
            <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full text-xs">
              HITL Learning
            </span>
            <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs">
              Real-time Streaming
            </span>
            {conversationHistory.length > 0 && (
              <span className="px-2 py-0.5 bg-orange-100 text-orange-700 rounded-full text-xs">
                Context: {conversationHistory.length} msgs
              </span>
            )}
            {currentStreamSession && (
              <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs animate-pulse">
                Live
              </span>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.length === 0 ? (
            <WelcomeScreen 
              onSendMessage={handleSendMessage} 
              loading={loading}
              streamingEnabled={true}
            />
          ) : (
            <>
              {messages.map((message, index) => (
                <MessageBubble
                  key={message.id || index}
                  message={message}
                  onFeedback={handleFeedback}
                  solutionRef={message.solution || message.streaming_session_id ? solutionRef : null}
                  isStreaming={loading && message.streaming_session_id === currentStreamSession}
                  allMessages={messages}                    
                  conversationHistory={conversationHistory} 
                />
              ))}

              {loading && !currentStreamSession && (
                <div className="flex justify-start">
                  <div className="bg-white border rounded-lg p-4 shadow-sm max-w-xs">
                    <div className="flex items-center gap-3 text-gray-500">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                      <span className="text-sm">Processing your question...</span>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>
      </main>

      <ChatInput 
        input={input}
        setInput={setInput}
        onSendMessage={handleSendMessage}
        loading={loading}
        streamingActive={currentStreamSession !== null}
        placeholder={
          currentStreamSession 
            ? "Please wait for the current solution to complete..." 
            : conversationHistory.length > 0
            ? "Continue the conversation..."
            : "Ask me any math question..."
        }
      />
    </div>
  );
}

export default ChatInterface;
