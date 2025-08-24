import React, { useRef, useEffect } from 'react';

function ChatInput({ 
  input, 
  setInput, 
  onSendMessage, 
  loading, 
  streamingActive, 
  placeholder 
}) {
  const textareaRef = useRef(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const safeInput = input || '';
    if (safeInput.trim() && !loading && !streamingActive) {
      onSendMessage(safeInput.trim());
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <footer className="bg-white border-t p-4 shadow-lg">
      <div className="max-w-3xl mx-auto">
        <form onSubmit={handleSubmit} className="flex gap-3 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input || ''}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={placeholder || "Ask me any math question..."}
              disabled={loading || streamingActive}
              className="w-full p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:text-gray-500 max-h-32"
              rows={1}
            />
            {streamingActive && (
              <div className="absolute inset-0 bg-gray-50 bg-opacity-90 flex items-center justify-center rounded-lg">
                <div className="flex items-center gap-2 text-gray-600">
                  <div className="animate-spin w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                  <span className="text-sm">Streaming in progress...</span>
                </div>
              </div>
            )}
          </div>
          
          <button
            type="submit"
            disabled={!(input || '').trim() || loading || streamingActive}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors duration-200 flex items-center gap-2"
          >
            {loading || streamingActive ? (
              <>
                <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                <span className="hidden sm:inline">
                  {streamingActive ? 'Streaming...' : 'Processing...'}
                </span>
              </>
            ) : (
              <>
                <span>Send</span>
                <span className="text-sm opacity-75 hidden sm:inline">Enter</span>
              </>
            )}
          </button>
        </form>
        
        {streamingActive && (
          <div className="mt-2 text-xs text-center text-orange-600">
            Real-time streaming active - please wait for completion
          </div>
        )}
        
        <div className="mt-2 text-xs text-center text-gray-500">
          Press Enter to send, Shift+Enter for new line
        </div>
      </div>
    </footer>
  );
}

export default ChatInput;
