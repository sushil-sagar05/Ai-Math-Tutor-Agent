import React, { useState } from 'react';
import { submitFeedback } from '../services/feedbackAPI';
import { useMathContext } from '../contexts/MathContext';
import StarRating from './StarRating';

function FeedbackForm({ solution }) {
  const [rating, setRating] = useState(0);
  const [comments, setComments] = useState('');
  const [correctedAnswer, setCorrectedAnswer] = useState('');
  const [correctedSteps, setCorrectedSteps] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitMessage, setSubmitMessage] = useState('');
  const [submitError, setSubmitError] = useState('');
  const [showForm, setShowForm] = useState(false);

  const { state, dispatch } = useMathContext();

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!rating) {
      setSubmitError('Please provide a rating');
      return;
    }

    setIsSubmitting(true);
    setSubmitError('');

    try {
      const feedbackData = {
        question: solution.question,
        original_solution: solution,
        user_rating: rating,
        user_comment: comments || null,
        corrected_answer: correctedAnswer || null,
        corrected_steps: correctedSteps ? correctedSteps.split('\n').filter(s => s.trim()) : null,
      };

      const response = await submitFeedback(feedbackData);
      
      setSubmitMessage(
        response.improvement_triggered 
          ? ' Thank you! Your feedback will help improve the system!'
          : ' Thank you for your feedback!'
      );
      
      dispatch({ type: 'SET_FEEDBACK_SUBMITTED', payload: true });
      setRating(0);
      setComments('');
      setCorrectedAnswer('');
      setCorrectedSteps('');
      setShowForm(false);
      setTimeout(() => setSubmitMessage(''), 5000);
      
    } catch (error) {
      setSubmitError(error.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    setShowForm(false);
    setSubmitError('');
    setRating(0);
    setComments('');
    setCorrectedAnswer('');
    setCorrectedSteps('');
  };

  if (state.feedbackSubmitted && submitMessage) {
    return (
      <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-8">
        <div className="text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl"></span>
          </div>
          <h3 className="text-xl font-semibold text-green-800 mb-2">Thank You!</h3>
          <p className="text-green-700">{submitMessage}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
      <div className="px-8 py-6 bg-gradient-to-r from-purple-600 to-pink-600">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-2xl font-bold text-white mb-2 flex items-center">
              <span className="text-3xl mr-2"></span>
              Help Us Improve
            </h3>
            <p className="text-purple-100">
              Your feedback helps our AI learn and provide better solutions
            </p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="px-6 py-3 bg-white bg-opacity-20 hover:bg-opacity-30 text-white rounded-xl font-semibold transition-all duration-200 backdrop-blur-sm"
          >
            {showForm ? 'Hide Feedback' : ' Give Feedback'}
          </button>
        </div>
      </div>
      {showForm && (
        <div className="p-8">
          <form onSubmit={handleSubmit} className="space-y-8">
            <div>
              <label className="block text-lg font-semibold text-gray-900 mb-4">
                Rate this solution: <span className="text-red-500">*</span>
              </label>
              <div className="flex items-center justify-center p-6 bg-gray-50 rounded-xl">
                <StarRating rating={rating} onRatingChange={setRating} size="w-12 h-12" />
              </div>
            </div>
            <div>
              <label htmlFor="comments" className="block text-lg font-semibold text-gray-900 mb-3">
                Comments or suggestions (optional)
              </label>
              <textarea
                id="comments"
                rows={4}
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                placeholder="What could be improved? Were any steps unclear? Any suggestions?"
                className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all duration-200 resize-none"
              />
            </div>
            <div>
              <label htmlFor="correctedAnswer" className="block text-lg font-semibold text-gray-900 mb-3">
                Correct answer (if different)
              </label>
              <input
                id="correctedAnswer"
                type="text"
                value={correctedAnswer}
                onChange={(e) => setCorrectedAnswer(e.target.value)}
                placeholder="Provide the correct answer if you know it"
                className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all duration-200"
              />
            </div>
            <div>
              <label htmlFor="correctedSteps" className="block text-lg font-semibold text-gray-900 mb-3">
                Improved solution steps (optional)
              </label>
              <textarea
                id="correctedSteps"
                rows={4}
                value={correctedSteps}
                onChange={(e) => setCorrectedSteps(e.target.value)}
                placeholder="Suggest better solution steps, one per line"
                className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all duration-200 resize-none"
              />
            </div>
            {submitError && (
              <div className="p-4 bg-red-50 border-l-4 border-red-400 rounded-r-xl">
                <p className="text-red-700 font-medium">{submitError}</p>
              </div>
            )}
            <div className="flex flex-col sm:flex-row gap-4 pt-6">
              <button
                type="submit"
                disabled={isSubmitting || !rating}
                className="flex-1 px-8 py-4 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-xl font-semibold text-lg shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105"
              >
                {isSubmitting ? (
                  <div className="flex items-center justify-center space-x-3">
                    <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>Submitting...</span>
                  </div>
                ) : (
                  <div className="flex items-center justify-center space-x-3">
                    <span className="text-2xl"></span>
                    <span>Submit Feedback</span>
                  </div>
                )}
              </button>
              
              <button
                type="button"
                onClick={handleCancel}
                disabled={isSubmitting}
                className="px-8 py-4 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl font-semibold text-lg transition-all duration-200 transform hover:scale-105"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

export default FeedbackForm;
