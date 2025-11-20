import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Filter,
  Search,
  Download,
  ArrowUpDown,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';
import { useDashboardStore } from '@/store/dashboard';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import {
  formatIDR,
  formatPercent,
  formatWIBDateTime,
  getSignalColorClass,
  formatStockCode,
} from '@/lib/utils';
import type { SignalType } from '@/types/api';

interface FilterState {
  search: string;
  signalType: SignalType | 'ALL';
  sortBy: 'composite_score' | 'confidence' | 'stock_code' | 'generated_at';
  sortOrder: 'asc' | 'desc';
  dateFrom: string;
  dateTo: string;
}

const Signals: React.FC = () => {
  const { signals, fetchSignals, isLoading } = useDashboardStore();
  const [filters, setFilters] = useState<FilterState>({
    search: '',
    signalType: 'ALL',
    sortBy: 'composite_score',
    sortOrder: 'desc',
    dateFrom: '',
    dateTo: '',
  });
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    fetchSignals();
  }, [fetchSignals]);

  // Filter and sort signals
  const filteredSignals = React.useMemo(() => {
    let filtered = [...(signals || [])];

    // Search filter
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter((signal) =>
        signal.stock_code.toLowerCase().includes(searchLower) ||
        signal.sector?.toLowerCase().includes(searchLower)
      );
    }

    // Signal type filter
    if (filters.signalType !== 'ALL') {
      filtered = filtered.filter((signal) => signal.signal_type === filters.signalType);
    }

    // Sort
    filtered.sort((a, b) => {
      const aVal = a[filters.sortBy];
      const bVal = b[filters.sortBy];
      
      let comparison = 0;
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        comparison = aVal.localeCompare(bVal);
      } else if (typeof aVal === 'number' && typeof bVal === 'number') {
        comparison = aVal - bVal;
      }
      
      return filters.sortOrder === 'desc' ? -comparison : comparison;
    });

    return filtered;
  }, [signals, filters]);

  const handleFilterChange = (key: keyof FilterState, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const clearFilters = () => {
    setFilters({
      search: '',
      signalType: 'ALL',
      sortBy: 'composite_score',
      sortOrder: 'desc',
      dateFrom: '',
      dateTo: '',
    });
  };

  const getSignalIcon = (signalType: SignalType) => {
    switch (signalType) {
      case 'STRONG_BUY':
      case 'BUY':
        return <TrendingUp className="h-4 w-4" />;
      case 'STRONG_SELL':
      case 'SELL':
        return <TrendingDown className="h-4 w-4" />;
      default:
        return <Minus className="h-4 w-4" />;
    }
  };

  const exportSignals = () => {
    // Convert to CSV
    const headers = [
      'Stock Code',
      'Signal Type',
      'Composite Score',
      'Confidence',
      'Position Size',
      'Current Price',
      'Sector',
      'Generated At',
    ];
    
    const csvData = filteredSignals.map(signal => [
      formatStockCode(signal.stock_code),
      signal.signal_type,
      signal.composite_score.toFixed(3),
      formatPercent(signal.confidence),
      formatPercent(signal.position_size),
      formatIDR(signal.current_price),
      signal.sector || '',
      formatWIBDateTime(signal.generated_at),
    ]);
    
    const csvContent = [headers, ...csvData]
      .map(row => row.join(','))
      .join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `trading-signals-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-secondary-900 mb-2">
            Trading Signals
          </h1>
          <p className="text-secondary-600">
            View and analyze daily trading recommendations
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
          >
            <Filter className="h-4 w-4 mr-2" />
            Filters
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={exportSignals}
            disabled={filteredSignals.length === 0}
          >
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Filters & Search</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Search */}
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-2">
                    Search
                  </label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-secondary-400" />
                    <input
                      type="text"
                      placeholder="Stock code or sector..."
                      value={filters.search}
                      onChange={(e) => handleFilterChange('search', e.target.value)}
                      className="w-full pl-10 pr-3 py-2 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                </div>

                {/* Signal Type */}
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-2">
                    Signal Type
                  </label>
                  <select
                    value={filters.signalType}
                    onChange={(e) => handleFilterChange('signalType', e.target.value)}
                    className="w-full px-3 py-2 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="ALL">All Signals</option>
                    <option value="STRONG_BUY">Strong Buy</option>
                    <option value="BUY">Buy</option>
                    <option value="HOLD">Hold</option>
                    <option value="SELL">Sell</option>
                    <option value="STRONG_SELL">Strong Sell</option>
                  </select>
                </div>

                {/* Sort By */}
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-2">
                    Sort By
                  </label>
                  <select
                    value={filters.sortBy}
                    onChange={(e) => handleFilterChange('sortBy', e.target.value)}
                    className="w-full px-3 py-2 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="composite_score">Composite Score</option>
                    <option value="confidence">Confidence</option>
                    <option value="stock_code">Stock Code</option>
                    <option value="generated_at">Date Generated</option>
                  </select>
                </div>

                {/* Sort Order */}
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-2">
                    Sort Order
                  </label>
                  <Button
                    variant="outline"
                    onClick={() => handleFilterChange('sortOrder', filters.sortOrder === 'asc' ? 'desc' : 'asc')}
                    className="w-full justify-center"
                  >
                    <ArrowUpDown className="h-4 w-4 mr-2" />
                    {filters.sortOrder === 'asc' ? 'Ascending' : 'Descending'}
                  </Button>
                </div>
              </div>

              <div className="flex justify-end mt-4">
                <Button variant="ghost" onClick={clearFilters}>
                  Clear Filters
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Results Summary */}
      <div className="flex items-center justify-between text-sm text-secondary-600">
        <span>
          Showing {filteredSignals.length} of {signals.length} signals
        </span>
        {signals.length > 0 && (
          <span>
            Last updated: {formatWIBDateTime(signals[0]?.generated_at || new Date())}
          </span>
        )}
      </div>

      {/* Signals Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner />
            </div>
          ) : filteredSignals.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-secondary-500">
                {signals.length === 0 ? 'No signals available' : 'No signals match your filters'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-secondary-50 border-b border-secondary-200">
                  <tr>
                    <th className="text-left px-6 py-3 text-sm font-medium text-secondary-700">
                      Stock
                    </th>
                    <th className="text-left px-6 py-3 text-sm font-medium text-secondary-700">
                      Signal
                    </th>
                    <th className="text-right px-6 py-3 text-sm font-medium text-secondary-700">
                      Score
                    </th>
                    <th className="text-right px-6 py-3 text-sm font-medium text-secondary-700">
                      Confidence
                    </th>
                    <th className="text-right px-6 py-3 text-sm font-medium text-secondary-700">
                      Position
                    </th>
                    <th className="text-right px-6 py-3 text-sm font-medium text-secondary-700">
                      Price
                    </th>
                    <th className="text-left px-6 py-3 text-sm font-medium text-secondary-700">
                      Sector
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-secondary-200">
                  {filteredSignals.map((signal, index) => (
                    <motion.tr
                      key={signal.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="hover:bg-secondary-50 transition-colors"
                    >
                      <td className="px-6 py-4">
                        <div>
                          <div className="font-medium text-secondary-900">
                            {formatStockCode(signal.stock_code)}
                          </div>
                          <div className="text-sm text-secondary-500">
                            {formatWIBDateTime(signal.generated_at).split(' ')[1]}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <Badge
                          className={`${getSignalColorClass(signal.signal_type)} flex items-center gap-1 w-fit`}
                        >
                          {getSignalIcon(signal.signal_type)}
                          {signal.signal_type.replace('_', ' ')}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="font-medium text-secondary-900">
                          {signal.composite_score.toFixed(3)}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="font-medium text-secondary-900">
                          {formatPercent(signal.confidence)}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="font-medium text-secondary-900">
                          {formatPercent(signal.position_size)}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="font-medium text-secondary-900">
                          {formatIDR(signal.current_price)}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-secondary-600">
                          {signal.sector || '-'}
                        </div>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default Signals;
