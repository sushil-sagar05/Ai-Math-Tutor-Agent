import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

function StreamingSolutionDisplay({ 
  sessionId, 
  question, 
  onComplete, 
  solution, 
  isStatic, 
  conversationHistory = [],  // ADDED: Accept conversation history
  messages = []              // ADDED: Accept parent messages for context
}) {
  const [streamedSteps, setStreamedSteps] = useState([]);
  const [finalSolution, setFinalSolution] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [routeInfo, setRouteInfo] = useState(null);
  const streamCleanupRef = useRef(null);

  useEffect(() => {
    console.log('🔄 StreamingSolutionDisplay useEffect triggered with:', { 
      sessionId, 
      question, 
      isStatic, 
      solution: !!solution,
      conversationHistory: conversationHistory?.length || 0,
      messages: messages?.length || 0
    });

    if (isStatic && solution) {
      console.log('✅ Using static solution mode');
      setFinalSolution(solution);
      setIsStreaming(false);
      setProgress(100);
      return;
    }

    if (!sessionId) {
      console.warn('⚠️ No sessionId provided - streaming will not start');
      return;
    }

    console.log('🚀 Starting streaming for sessionId:', sessionId);
    setIsStreaming(true);
    setStreamedSteps([]);
    setFinalSolution(null);
    setProgress(0);

    const startStream = async () => {
      try {
        console.log('📦 Importing createStreamConnection...');
        const { createStreamConnection } = await import('../../services/mathAPI');
        let fullConversationHistory = conversationHistory;
        if (!fullConversationHistory || fullConversationHistory.length === 0) {
          fullConversationHistory = messages
            .filter(msg => msg.text && msg.text.trim()) 
            .map(msg => ({
              role: msg.isUser ? 'user' : 'assistant',
              content: msg.text,
              request_type: msg.request_type || 'unknown'
            }));
        }

        console.log(' Using conversation history:', {
          length: fullConversationHistory.length,
          sessionId: sessionId,
          question: question?.substring(0, 50) + '...'
        });

        fullConversationHistory.forEach((msg, i) => {
          console.log(`  [${i}] ${msg.role}: ${msg.content?.substring(0, 50)}...`);
        });
        
        console.log(' Creating stream connection...');
        const cleanup = await createStreamConnection(
          question,
          sessionId,
          {
            onConnect: (data) => {
              console.log(' Stream connected:', data);
            },
            onProcessingStart: (data) => {
              console.log(' Processing started:', data);
              setCurrentStep(data.message || 'Starting to solve your math problem...');
              setProgress(10);
            },
            onRouting: (data) => {
              console.log(' Routing:', data);
              setCurrentStep(data.message || 'Checking knowledge base for similar problems...');
              setProgress(25);
            },
            onRoutingResult: (data) => {
              console.log(' Routing result:', data);
              setRouteInfo(data);
              setCurrentStep(data.message || `Using ${data.route} route (${(data.confidence * 100).toFixed(1)}% confidence)`);
              setProgress(40);
            },
            onStepUpdate: (data) => {
              console.log(' Step update:', data);
              setCurrentStep(data.message);
              setProgress(data.progress || 50);
            },
            onStepGenerated: (data) => {
              console.log(' Step generated:', data);
              setStreamedSteps(prev => [...prev, {
                ...data.step_data,
                stepNumber: data.step_number,
                isStreaming: true
              }]);
              setProgress(50 + (data.step_number / data.total_steps) * 30);
            },
            onSolutionComplete: (data) => {
              console.log(' Solution complete:', data);
              setFinalSolution(data.data);
              setCurrentStep('Solution complete!');
              setProgress(100);
              setIsStreaming(false);
              if (onComplete) onComplete(data.data);
            },
            onCompletion: (data) => {
              console.log(' Completion:', data);
              setCurrentStep(data.message || 'Finalizing solution...');
              setProgress(data.progress || 95);
            },
            onError: (data) => {
              console.error(' Stream error:', data);
              setCurrentStep(`Error: ${data.message}`);
              setIsStreaming(false);
            },
            onConnectionError: (error) => {
              console.error(' Connection error:', error);
              setCurrentStep('Connection error occurred');
              setIsStreaming(false);
            }
          },
          fullConversationHistory 
        );

        console.log(' Stream connection created successfully');
        streamCleanupRef.current = cleanup;

      } catch (error) {
        console.error(' Failed to start stream:', error);
        setCurrentStep('Failed to start streaming');
        setIsStreaming(false);
      }
    };

    startStream();

    return () => {
      console.log(' Cleaning up stream for sessionId:', sessionId);
      if (streamCleanupRef.current) {
        streamCleanupRef.current();
      }
    };
  }, [sessionId, question, onComplete, solution, isStatic, conversationHistory, messages]);

  const displaySolution = finalSolution || solution || {
    steps: streamedSteps,
    route: routeInfo?.route,
    confidence: routeInfo?.confidence
  };

  const hasSteps = streamedSteps.length > 0 || (displaySolution?.steps?.length > 0);
  const confidence = displaySolution.confidence || displaySolution.confidence_score || 0;

  console.log(' StreamingSolutionDisplay State:', {
    isStreaming,
    progress,
    currentStep,
    streamedSteps: streamedSteps.length,
    hasSteps,
    finalSolution: !!finalSolution,
    sessionId,
    contextAvailable: conversationHistory?.length > 0 || messages?.length > 0
  });

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-4 py-3">
        <h3 className="font-semibold flex items-center justify-between">
          <div className="flex items-center">
            <span className="text-xl mr-2">📋</span>
            <span>Step-by-Step Solution</span>
            {(conversationHistory?.length > 0 || messages?.length > 1) && (
              <span className="ml-2 px-2 py-1 bg-white bg-opacity-20 rounded-full text-xs">
                Context-Aware
              </span>
            )}
          </div>
          {isStreaming && (
            <div className="flex items-center gap-2">
              <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
              <span className="text-sm">Solving...</span>
            </div>
          )}
        </h3>
      </div>

      {isStreaming && (
        <div className="px-4 py-3 bg-blue-50 border-b">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-blue-900">{currentStep}</span>
            <span className="text-sm text-blue-700">{progress}%</span>
          </div>
          <div className="w-full bg-blue-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>
      )}

      {(routeInfo || displaySolution.route) && (
        <div className="px-4 py-2 bg-gray-50 border-b border-gray-200">
          <div className="flex flex-wrap gap-2">
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
              (routeInfo?.route || displaySolution.route) === 'knowledge_base'
                ? 'bg-green-100 text-green-800' 
                : 'bg-blue-100 text-blue-800'
            }`}>
              {(routeInfo?.route || displaySolution.route) === 'knowledge_base' ? 'Knowledge Base' : 'Web Search'}
            </span>
            
            <span className="px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
              Confidence: {(confidence * 100).toFixed(1)}%
            </span>
            
            {(displaySolution.enhanced_by_dspy || displaySolution.dspy_enhanced) && (
              <span className="px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                AI Enhanced
              </span>
            )}

            {(conversationHistory?.length > 0 || messages?.length > 1) && (
              <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                Context: {conversationHistory?.length || messages?.length || 0} msgs
              </span>
            )}
          </div>
        </div>
      )}

      {hasSteps ? (
        <div className="px-4 py-4">
          <div className="space-y-3">
            {(displaySolution?.steps || streamedSteps).map((step, index) => (
              <StreamingStepItem 
                key={index}
                step={step}
                stepNumber={step.stepNumber || step.step || index + 1}
                isLast={index === (displaySolution?.steps || streamedSteps).length - 1}
                isStreaming={step.isStreaming && isStreaming}
              />
            ))}
            
            {isStreaming && streamedSteps.length === 0 && (
              <div className="flex items-center justify-center py-8">
                <div className="text-center">
                  <div className="animate-spin w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full mb-4"></div>
                  <div className="text-gray-600">Generating solution steps...</div>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="px-4 py-4">
          <div className="text-center py-8">
            {isStreaming ? (
              <div>
                <div className="animate-spin w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full mx-auto mb-4"></div>
                <div className="text-gray-600 mb-2">Processing your question...</div>
                <div className="text-sm text-gray-500">This may take a few moments</div>
              </div>
            ) : (
              <div>
                <div className="text-4xl mb-3">🔍</div>
                <div className="text-gray-600 mb-2">No detailed steps available</div>
                <div className="text-sm text-gray-500">
                  The solution was generated but step-by-step breakdown is not available
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {(displaySolution?.final_answer || (!isStreaming && streamedSteps.length > 0)) && (
        <div className="bg-gradient-to-r from-green-50 to-emerald-50 border-t border-gray-200 px-4 py-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-2xl">🎯</span>
            <h4 className="font-semibold text-green-900">Final Answer:</h4>
          </div>
          <div className="bg-white rounded-lg p-4 border-2 border-green-300 shadow-sm">
            <div className="text-lg font-bold text-green-800 text-center">
              <ReactMarkdown 
                remarkPlugins={[remarkMath]}
                rehypePlugins={[rehypeKatex]}
                components={{
                  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                  strong: ({ children }) => (
                    <strong className="text-green-900 font-bold">{children}</strong>
                  ),
                }}
              >
                {displaySolution?.final_answer || 'See detailed steps above'}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StreamingStepItem({ step, stepNumber, isLast, isStreaming }) {
  return (
    <div className={`flex gap-3 ${isStreaming ? 'animate-fadeIn' : ''}`}>
      <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 text-white flex items-center justify-center rounded-full text-sm font-bold flex-shrink-0">
        {isStreaming ? (
          <div className="animate-pulse">●</div>
        ) : (
          stepNumber
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className={`bg-gray-50 rounded-lg p-4 border border-gray-200 transition-all duration-300 ${
          isStreaming ? 'border-blue-300 bg-blue-50' : 'hover:shadow-sm'
        }`}>
          <div className="prose prose-sm max-w-none text-gray-800">
            <ReactMarkdown 
              remarkPlugins={[remarkMath]}
              rehypePlugins={[rehypeKatex]}
              components={{
                p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                code: ({ children }) => (
                  <code className="bg-gray-200 px-1 py-0.5 rounded text-sm font-mono">
                    {children}
                  </code>
                ),
                strong: ({ children }) => (
                  <strong className="text-gray-900 font-semibold">{children}</strong>
                ),
              }}
            >
              {step.text}
            </ReactMarkdown>
          </div>
          
          {step.type && step.type !== 'solution_step' && step.type !== 'educational_step' && (
            <div className="mt-3">
              <span className="px-2 py-1 text-xs font-medium rounded-full bg-purple-100 text-purple-800">
                {step.type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </span>
            </div>
          )}
          
          {isLast && !isStreaming && (
            <div className="mt-3 pt-2 border-t border-gray-200">
              <div className="text-xs text-gray-500 flex items-center gap-1">
                <span>✅</span>
                <span>Solution complete</span>
              </div>
            </div>
          )}
        </div>
        
        {!isLast && (
          <div className="flex justify-center my-2">
            <div className="w-px h-4 bg-gray-300"></div>
          </div>
        )}
      </div>
    </div>
  );
}

export default StreamingSolutionDisplay;
