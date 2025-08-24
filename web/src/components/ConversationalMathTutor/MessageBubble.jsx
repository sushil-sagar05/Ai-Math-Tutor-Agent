import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import StreamingSolutionDisplay from './SolutionDisplay';
import FeedbackPanel from './FeedbackPanel';

function MessageBubble({ 
  message, 
  onFeedback, 
  solutionRef, 
  isStreaming, 
  allMessages = [],        
  conversationHistory = [] 
}) {
  const [streamingSessionId, setStreamingSessionId] = useState(null);
  const [showStreamingSolution, setShowStreamingSolution] = useState(false);

  useEffect(() => {
    console.log(' MessageBubble useEffect:', {
      messageId: message.id,
      hasStreamingSessionId: !!message.streaming_session_id,
      hasSolution: !!message.solution,
      streamingSessionId: message.streaming_session_id,
      allMessagesCount: allMessages.length,
      conversationHistoryCount: conversationHistory.length
    });

    if (message.streaming_session_id && !message.solution) {
      console.log(' Setting up streaming for session:', message.streaming_session_id);
      setStreamingSessionId(message.streaming_session_id);
      setShowStreamingSolution(true);
    } else if (message.solution) {
      console.log(' Message has completed solution, not showing streaming');
      setShowStreamingSolution(false);
      setStreamingSessionId(null);
    }
  }, [message, allMessages.length, conversationHistory.length]);

  const handleStreamingComplete = (completedSolution) => {
    console.log(' Streaming completed for message:', message.id, completedSolution);
    
    if (message.onSolutionComplete) {
      message.onSolutionComplete(completedSolution);
    }
    setShowStreamingSolution(false);
    setStreamingSessionId(null);
  };

  const buildConversationHistory = () => {
    if (conversationHistory && conversationHistory.length > 0) {
      console.log(' Using explicit conversation history:', conversationHistory.length);
      return conversationHistory;
    }
    if (allMessages && allMessages.length > 0) {
      const messageIndex = allMessages.findIndex(msg => msg.id === message.id);
      const messagesUpToHere = messageIndex >= 0 ? allMessages.slice(0, messageIndex) : allMessages;
      
      const history = messagesUpToHere
        .filter(msg => msg.text && msg.text.trim()) 
        .map(msg => ({
          role: msg.isUser ? 'user' : 'assistant',
          content: msg.text,
          request_type: msg.request_type || 'unknown'
        }));

      console.log(' Built conversation history from messages:', history.length);
      return history;
    }

    console.log(' No conversation history available');
    return [];
  };

  const contextHistory = buildConversationHistory();

  console.log(' MessageBubble render state:', {
    messageId: message.id,
    showStreamingSolution,
    streamingSessionId,
    isStreaming,
    hasSolution: !!message.solution,
    contextHistoryLength: contextHistory.length
  });

  return (
    <div className={`flex ${message.isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className="max-w-[85%] space-y-3">
        <div 
          className={`p-4 rounded-2xl shadow-sm transition-all duration-200 ${
            message.isUser 
              ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-br-sm' 
              : message.isError 
              ? 'bg-red-50 border border-red-200 text-red-700 rounded-bl-sm' 
              : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm hover:shadow-md'
          }`}
        >
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown 
              remarkPlugins={[remarkMath]}
              rehypePlugins={[rehypeKatex]}
              components={{
                p: ({ children }) => (
                  <p className={`mb-2 last:mb-0 ${message.isUser ? 'text-white' : 'text-gray-800'}`}>
                    {children}
                  </p>
                ),
                strong: ({ children }) => (
                  <strong className={message.isUser ? 'text-white font-semibold' : 'text-gray-900 font-semibold'}>
                    {children}
                  </strong>
                ),
                code: ({ children }) => (
                  <code className={`px-2 py-1 rounded text-sm font-mono ${
                    message.isUser 
                      ? 'bg-blue-700 text-blue-100' 
                      : 'bg-gray-200 text-gray-800'
                  }`}>
                    {children}
                  </code>
                ),
              }}
            >
              {message.text}
            </ReactMarkdown>
          </div>
          
          {message.timestamp && (
            <div className={`text-xs mt-2 ${
              message.isUser ? 'text-blue-100' : 'text-gray-500'
            }`}>
              {message.timestamp.toLocaleTimeString([], { 
                hour: '2-digit', 
                minute: '2-digit' 
              })}
            </div>
          )}
        </div>

        {!message.isUser && process.env.NODE_ENV === 'development' && (
          <div className="text-xs text-gray-500 bg-gray-100 p-2 rounded">
            Debug: SessionId={streamingSessionId}, ShowStreaming={showStreamingSolution.toString()}, 
            HasSolution={!!message.solution}, ContextHistory={contextHistory.length} msgs
          </div>
        )}
        {showStreamingSolution && streamingSessionId && (
          <div ref={solutionRef} className="animate-fadeIn">
            <StreamingSolutionDisplay 
              sessionId={streamingSessionId}
              question={message.originalQuestion}
              onComplete={handleStreamingComplete}
              conversationHistory={contextHistory} 
              messages={allMessages}              
            />
          </div>
        )}

        {message.solution && !showStreamingSolution && (
          <div ref={solutionRef} className="animate-fadeIn">
            <StreamingSolutionDisplay 
              solution={message.solution}
              isStatic={true}
              conversationHistory={contextHistory} 
              messages={allMessages}              
            />
          </div>
        )}

        {message.showFeedback && !message.feedbackSubmitted && !message.isUser && message.solution && (
          <div className="animate-slideIn">
            <FeedbackPanel 
              messageId={message.id}
              question={message.originalQuestion}
              solution={message.solution}
              onSubmitFeedback={onFeedback}
            />
          </div>
        )}

        {message.feedbackSubmitted && (
          <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-lg p-3 animate-fadeIn">
            <div className="flex items-center gap-2 text-green-700">
              <span className="text-lg">✓</span>
              <span className="text-sm font-medium">Thanks for your feedback! It helps me learn.</span>
            </div>
            {message.feedbackDetails && (
              <div className="mt-2 text-xs text-green-600">
                Rating: {message.feedbackDetails.rating}/5
                {message.feedbackDetails.improvement_triggered && " • Learning triggered"}
              </div>
            )}
          </div>
        )}

        {isStreaming && !message.isUser && !showStreamingSolution && (
          <div className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-full text-gray-600 text-sm animate-pulse">
            <div className="flex gap-1">
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
            <span>AI is thinking...</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default MessageBubble;
