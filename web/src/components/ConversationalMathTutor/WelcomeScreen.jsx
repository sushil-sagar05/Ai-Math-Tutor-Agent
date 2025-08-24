import React from 'react';

const SAMPLE_QUESTIONS = [
  "Expand (2x+3)(x-1)",
  "What is the derivative of sin(x)?",
  "Solve 2x + 5 = 11",
  "Explain the Pythagorean theorem"
];

function WelcomeScreen({ onSendMessage, loading }) {
  return (
    <div className="text-center py-12">
      <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-6">
        <span className="text-3xl font-bold text-blue-600">AI</span>
      </div>
      
      <h2 className="text-2xl font-bold text-gray-900 mb-2">
        Welcome to your AI Math Tutor
      </h2>
      
      <p className="text-gray-600 mb-8 max-w-lg mx-auto">
        Ask me any math question and I'll provide detailed explanations. 
        You can follow up with clarifications or ask for different approaches.
      </p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl mx-auto">
        {SAMPLE_QUESTIONS.map((sample, index) => (
          <SampleQuestionButton
            key={index}
            question={sample}
            onClick={() => onSendMessage(sample)}
            disabled={loading}
          />
        ))}
      </div>
      
      <div className="mt-8 text-sm text-gray-500">
        Try starting with one of these sample questions or type your own.
      </div>
    </div>
  );
}

function SampleQuestionButton({ question, onClick, disabled }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="p-4 text-left bg-white border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed group"
    >
      <div className="flex items-start gap-3">
        <span className="w-2 h-2 rounded-full bg-blue-400 mt-2"></span>
        <span className="text-blue-600 font-medium group-hover:text-blue-700">
          {question}
        </span>
      </div>
    </button>
  );
}

export default WelcomeScreen;
