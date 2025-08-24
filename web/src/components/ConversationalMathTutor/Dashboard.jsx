import React, { useState, useEffect } from 'react';
import { getLearningStats, getSystemStatus } from '../services/mathAPI';

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [statsData, statusData] = await Promise.all([
          getLearningStats(),
          getSystemStatus()
        ]);
        setStats(statsData);
        setSystemStatus(statusData);
      } catch (error) {
        setError(error.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4"></div>
          <p className="text-gray-600 text-lg">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-xl p-8 text-center max-w-md">
          <h3 className="text-xl font-semibold text-red-900 mb-2">Error loading dashboard</h3>
          <p className="text-red-700">{error}</p>
        </div>
      </div>
    );
  }

  if (!stats || stats.status === 'no_feedback') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-xl p-12 text-center max-w-2xl">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">No Analytics Available</h2>
          <p className="text-gray-600 text-lg mb-8">
            Start by solving problems and submitting feedback to see learning analytics!
          </p>
          <div className="bg-blue-50 border-2 border-blue-200 rounded-xl p-6">
            <p className="text-blue-800 font-medium">
              Tip: The more feedback you provide, the better our AI becomes at solving math problems.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'ready': case 'active': case 'operational': case 'enabled': return 'text-green-600 bg-green-100';
      case 'warning': case 'disabled': return 'text-yellow-600 bg-yellow-100';
      case 'error': case 'unavailable': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Learning Analytics</h1>
          <p className="text-xl text-gray-600">
            Human-in-the-Loop performance metrics and system status
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          <div className="bg-white rounded-2xl shadow-lg p-8 border border-gray-100 text-center transform hover:scale-105 transition-all duration-200">
            <div className="text-3xl font-bold text-gray-900 mb-2">
              {stats.average_rating?.toFixed(1) || 'N/A'}
            </div>
            <div className="text-gray-600 font-medium">Average Rating</div>
          </div>

          <div className="bg-white rounded-2xl shadow-lg p-8 border border-gray-100 text-center transform hover:scale-105 transition-all duration-200">
            <div className="text-3xl font-bold text-gray-900 mb-2">
              {stats.total_feedback || 0}
            </div>
            <div className="text-gray-600 font-medium">Total Feedback</div>
          </div>

          <div className="bg-white rounded-2xl shadow-lg p-8 border border-gray-100 text-center transform hover:scale-105 transition-all duration-200">
            <div className="text-3xl font-bold text-gray-900 mb-2">
              {((stats.kb_accuracy || 0) * 100).toFixed(0)}%
            </div>
            <div className="text-gray-600 font-medium">KB Accuracy</div>
          </div>

          <div className="bg-white rounded-2xl shadow-lg p-8 border border-gray-100 text-center transform hover:scale-105 transition-all duration-200">
            <div className="text-3xl font-bold text-gray-900 mb-2">
              {((stats.web_accuracy || 0) * 100).toFixed(0)}%
            </div>
            <div className="text-gray-600 font-medium">Web Accuracy</div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
          <div className="bg-white rounded-2xl shadow-lg p-8 border border-gray-100">
            <h3 className="text-2xl font-bold text-gray-900 mb-6">Learning Status</h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-4 bg-gray-50 rounded-xl">
                <span className="font-medium text-gray-700">Learning Mode:</span>
                <span className={`px-3 py-1 rounded-full font-semibold ${
                  stats.learning_status === 'active' ? 'text-green-700 bg-green-100' : 'text-yellow-700 bg-yellow-100'
                }`}>
                  {stats.learning_status || 'Unknown'}
                </span>
              </div>
              <div className="flex justify-between items-center p-4 bg-gray-50 rounded-xl">
                <span className="font-medium text-gray-700">High Ratings (4-5):</span>
                <span className="font-bold text-green-600">{stats.high_ratings || 0}</span>
              </div>
              <div className="flex justify-between items-center p-4 bg-gray-50 rounded-xl">
                <span className="font-medium text-gray-700">Low Ratings (1-2):</span>
                <span className="font-bold text-red-600">{stats.low_ratings || 0}</span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-lg p-8 border border-gray-100">
            <h3 className="text-2xl font-bold text-gray-900 mb-6">System Status</h3>
            {systemStatus ? (
              <div className="space-y-4">
                <div className="flex justify-between items-center p-4 bg-gray-50 rounded-xl">
                  <span className="font-medium text-gray-700">Knowledge Base:</span>
                  <span className={`px-3 py-1 rounded-full font-semibold ${getStatusColor(systemStatus.knowledge_base)}`}>
                    {systemStatus.knowledge_base}
                  </span>
                </div>
                <div className="flex justify-between items-center p-4 bg-gray-50 rounded-xl">
                  <span className="font-medium text-gray-700">Web Search:</span>
                  <span className={`px-3 py-1 rounded-full font-semibold ${getStatusColor(systemStatus.mcp_web_search)}`}>
                    {systemStatus.mcp_web_search}
                  </span>
                </div>
                <div className="flex justify-between items-center p-4 bg-gray-50 rounded-xl">
                  <span className="font-medium text-gray-700">HITL System:</span>
                  <span className={`px-3 py-1 rounded-full font-semibold ${getStatusColor(systemStatus.hitl_system?.feedback_collection)}`}>
                    {systemStatus.hitl_system?.feedback_collection || 'disabled'}
                  </span>
                </div>
                <div className="flex justify-between items-center p-4 bg-gray-50 rounded-xl">
                  <span className="font-medium text-gray-700">Learning Mode:</span>
                  <span className="px-3 py-1 rounded-full font-semibold text-purple-700 bg-purple-100">
                    {systemStatus.learning_mode || 'static'}
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">System status unavailable</p>
            )}
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-lg p-8 border border-gray-100">
          <h3 className="text-2xl font-bold text-gray-900 mb-8">Performance Overview</h3>
          <div className="space-y-6">
            <div>
              <div className="flex justify-between text-lg font-semibold mb-2">
                <span>Knowledge Base Accuracy</span>
                <span>{((stats.kb_accuracy || 0) * 100).toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-4">
                <div 
                  className="bg-gradient-to-r from-green-400 to-green-600 h-4 rounded-full transition-all duration-1000 ease-out"
                  style={{ width: `${(stats.kb_accuracy || 0) * 100}%` }}
                ></div>
              </div>
            </div>
            
            <div>
              <div className="flex justify-between text-lg font-semibold mb-2">
                <span>Web Search Accuracy</span>
                <span>{((stats.web_accuracy || 0) * 100).toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-4">
                <div 
                  className="bg-gradient-to-r from-blue-400 to-blue-600 h-4 rounded-full transition-all duration-1000 ease-out"
                  style={{ width: `${(stats.web_accuracy || 0) * 100}%` }}
                ></div>
              </div>
            </div>
            
            <div>
              <div className="flex justify-between text-lg font-semibold mb-2">
                <span>Overall User Satisfaction</span>
                <span>{((stats.average_rating || 0) / 5 * 100).toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-4">
                <div 
                  className="bg-gradient-to-r from-purple-400 to-purple-600 h-4 rounded-full transition-all duration-1000 ease-out"
                  style={{ width: `${(stats.average_rating || 0) / 5 * 100}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
