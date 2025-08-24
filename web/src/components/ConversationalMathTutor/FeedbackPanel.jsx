import React, { useState } from 'react';

function FeedbackPanel({ messageId, onSubmitFeedback }) {
  const [showFeedback, setShowFeedback] = useState(false);
  const [rating, setRating] = useState(0);
  const [comments, setComments] = useState('');

  const handleSubmit = () => {
    if (rating > 0) {
      onSubmitFeedback(messageId, {
        user_rating: rating,
        user_comment: comments || null,
      });
      setShowFeedback(false);
      setRating(0);
      setComments('');
    }
  };

  const handleCancel = () => {
    setShowFeedback(false);
    setRating(0);
    setComments('');
  };

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
      {!showFeedback ? (
        <button
          onClick={() => setShowFeedback(true)}
          className="flex items-center gap-2 text-blue-600 hover:text-blue-700 font-medium transition-colors"
        >
          <span>💬</span>
          <span>Rate this response</span>
        </button>
      ) : (
        <div className="space-y-4">
          <h4 className="font-semibold text-gray-900">How was this response?</h4>
          <div className="flex items-center gap-1">
            {[1, 2, 3, 4, 5].map((star) => (
              <StarButton
                key={star}
                star={star}
                rating={rating}
                onClick={() => setRating(star)}
              />
            ))}
            <span className="ml-2 text-sm text-gray-600">
              {rating > 0 ? `${rating}/5` : 'Click to rate'}
            </span>
          </div>
          <textarea
            value={comments}
            onChange={(e) => setComments(e.target.value)}
            placeholder="Any suggestions for improvement? (optional)"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-100 resize-none text-sm"
            rows={2}
          />
          <div className="flex gap-3">
            <button
              onClick={handleSubmit}
              disabled={rating === 0}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-700 transition-colors text-sm"
            >
              Submit Feedback
            </button>
            <button
              onClick={handleCancel}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg font-medium hover:bg-gray-300 transition-colors text-sm"
            >
              Skip
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function StarButton({ star, rating, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`w-8 h-8 text-xl transition-colors ${
        star <= rating 
          ? 'text-yellow-400 hover:text-yellow-500' 
          : 'text-gray-300 hover:text-yellow-300'
      }`}
    >
      ⭐
    </button>
  );
}

export default FeedbackPanel;
