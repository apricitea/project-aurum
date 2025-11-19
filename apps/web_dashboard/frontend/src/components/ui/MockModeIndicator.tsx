import React from 'react';
import { AlertCircleIcon, DatabaseIcon } from 'lucide-react';
import { isMockMode } from '@/lib/api';

export const MockModeIndicator: React.FC = () => {
  if (!isMockMode) {
    return null; // Don't show anything in production mode
  }

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-gradient-to-r from-blue-600 to-purple-600 text-white p-3 shadow-lg">
      <div className="container mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <DatabaseIcon className="h-5 w-5 animate-pulse" />
          <span className="font-semibold text-sm">
            🎭 Standalone Mode - Demo Data
          </span>
          <span className="text-xs opacity-90 hidden sm:inline">
            (No Backend Connection)
          </span>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 text-xs">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            <span>Live Mock Data</span>
          </div>

          <div className="text-xs opacity-90">
            <span className="font-medium">Login:</span> demo/demo
          </div>
        </div>
      </div>

      {/* Push content down to avoid overlap */}
      <style jsx>{`
        body {
          padding-top: 52px;
        }
      `}</style>
    </div>
  );
};

export const MockModeBadge: React.FC<{ className?: string }> = ({ className = "" }) => {
  if (!isMockMode) {
    return null;
  }

  return (
    <div className={`inline-flex items-center space-x-2 px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium ${className}`}>
      <AlertCircleIcon className="h-3 w-3" />
      <span>Demo Data</span>
    </div>
  );
};