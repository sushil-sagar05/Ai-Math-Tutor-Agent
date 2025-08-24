import React, { createContext, useContext, useReducer, useCallback } from 'react';

const MathContext = createContext();

const initialState = {
  currentSolution: null,
  isLoading: false,
  error: null,
  feedbackSubmitted: false,
  learningStats: null,
  systemHealth: null,
  history: [], // Store solution history
};

function mathReducer(state, action) {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload, error: null };
    case 'SET_SOLUTION':
      return { 
        ...state, 
        currentSolution: action.payload, 
        isLoading: false,
        feedbackSubmitted: false,
        history: [action.payload, ...state.history.slice(0, 9)] // Keep last 10
      };
    case 'SET_ERROR':
      return { ...state, error: action.payload, isLoading: false };
    case 'SET_FEEDBACK_SUBMITTED':
      return { ...state, feedbackSubmitted: action.payload };
    case 'SET_LEARNING_STATS':
      return { ...state, learningStats: action.payload };
    case 'SET_SYSTEM_HEALTH':
      return { ...state, systemHealth: action.payload };
    case 'CLEAR_SOLUTION':
      return { ...state, currentSolution: null, feedbackSubmitted: false, error: null };
    case 'CLEAR_ERROR':
      return { ...state, error: null };
    default:
      return state;
  }
}

export function MathProvider({ children }) {
  const [state, dispatch] = useReducer(mathReducer, initialState);

  const clearError = useCallback(() => {
    dispatch({ type: 'CLEAR_ERROR' });
  }, []);

  const clearSolution = useCallback(() => {
    dispatch({ type: 'CLEAR_SOLUTION' });
  }, []);

  const value = {
    state,
    dispatch,
    clearError,
    clearSolution
  };

  return (
    <MathContext.Provider value={value}>
      {children}
    </MathContext.Provider>
  );
}

export function useMathContext() {
  const context = useContext(MathContext);
  if (!context) {
    throw new Error('useMathContext must be used within a MathProvider');
  }
  return context;
}
