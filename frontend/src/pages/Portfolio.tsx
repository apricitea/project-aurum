import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Plus,
  Edit,
  Trash2,
  PieChart,
  TrendingUp,
  TrendingDown,
  DollarSign,
  BarChart3,
} from 'lucide-react';
import { useDashboardStore } from '@/store/dashboard';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import {
  formatIDR,
  formatPercent,
  getPnLColorClass,
  formatStockCode,
} from '@/lib/utils';
import type { Position } from '@/types/api';

interface EditPositionModal {
  isOpen: boolean;
  position: Position | null;
}

const Portfolio: React.FC = () => {
  const {
    portfolio,
    positions,
    loadPortfolio,
    updatePosition,
    isLoading,
  } = useDashboardStore();
  
  const [editModal, setEditModal] = useState<EditPositionModal>({
    isOpen: false,
    position: null,
  });
  const [newPosition, setNewPosition] = useState({
    stock_code: '',
    quantity: 0,
    average_price: 0,
  });
  const [showAddForm, setShowAddForm] = useState(false);

  useEffect(() => {
    loadPortfolio();
  }, [loadPortfolio]);

  const handleUpdatePosition = async (position: Position) => {
    try {
      await updatePosition({
        stock_code: position.stock_code,
        quantity: position.quantity,
        average_price: position.average_price,
      });
      setEditModal({ isOpen: false, position: null });
    } catch (error) {
      console.error('Failed to update position:', error);
    }
  };

  const handleAddPosition = async () => {
    if (!newPosition.stock_code || newPosition.quantity <= 0 || newPosition.average_price <= 0) {
      return;
    }

    try {
      await updatePosition(newPosition);
      setNewPosition({ stock_code: '', quantity: 0, average_price: 0 });
      setShowAddForm(false);
    } catch (error) {
      console.error('Failed to add position:', error);
    }
  };

  const totalMarketValue = positions.reduce((sum, pos) => sum + (pos.market_value || 0), 0);
  const totalUnrealizedPnL = positions.reduce((sum, pos) => sum + (pos.unrealized_pnl || 0), 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-secondary-900 mb-2">
            Portfolio Management
          </h1>
          <p className="text-secondary-600">
            Track and manage your stock positions
          </p>
        </div>

        <Button
          onClick={() => setShowAddForm(!showAddForm)}
          className="flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          Add Position
        </Button>
      </div>

      {/* Add Position Form */}
      {showAddForm && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Add New Position</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-2">
                    Stock Code
                  </label>
                  <input
                    type="text"
                    placeholder="e.g., BBCA"
                    value={newPosition.stock_code}
                    onChange={(e) => setNewPosition(prev => ({ ...prev, stock_code: e.target.value.toUpperCase() }))}
                    className="w-full px-3 py-2 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-2">
                    Quantity
                  </label>
                  <input
                    type="number"
                    placeholder="Number of shares"
                    value={newPosition.quantity || ''}
                    onChange={(e) => setNewPosition(prev => ({ ...prev, quantity: parseInt(e.target.value) || 0 }))}
                    className="w-full px-3 py-2 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-2">
                    Average Price (IDR)
                  </label>
                  <input
                    type="number"
                    placeholder="Purchase price"
                    value={newPosition.average_price || ''}
                    onChange={(e) => setNewPosition(prev => ({ ...prev, average_price: parseFloat(e.target.value) || 0 }))}
                    className="w-full px-3 py-2 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-4">
                <Button variant="ghost" onClick={() => setShowAddForm(false)}>
                  Cancel
                </Button>
                <Button onClick={handleAddPosition}>
                  Add Position
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Portfolio Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-secondary-600">Total Value</p>
                <p className="text-2xl font-bold text-secondary-900">
                  {formatIDR(totalMarketValue)}
                </p>
              </div>
              <div className="h-12 w-12 bg-primary-100 rounded-lg flex items-center justify-center">
                <DollarSign className="h-6 w-6 text-primary-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-secondary-600">Unrealized P&L</p>
                <p className={`text-2xl font-bold ${getPnLColorClass(totalUnrealizedPnL)}`}>
                  {formatIDR(totalUnrealizedPnL)}
                </p>
                <p className={`text-sm ${getPnLColorClass(totalUnrealizedPnL)}`}>
                  {portfolio ? formatPercent(portfolio.total_unrealized_pnl_percent / 100) : '0%'}
                </p>
              </div>
              <div className="h-12 w-12 bg-success-100 rounded-lg flex items-center justify-center">
                {totalUnrealizedPnL >= 0 ? (
                  <TrendingUp className="h-6 w-6 text-success-600" />
                ) : (
                  <TrendingDown className="h-6 w-6 text-danger-600" />
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-secondary-600">Positions</p>
                <p className="text-2xl font-bold text-secondary-900">
                  {positions.length}
                </p>
              </div>
              <div className="h-12 w-12 bg-info-100 rounded-lg flex items-center justify-center">
                <PieChart className="h-6 w-6 text-info-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-secondary-600">Cash Available</p>
                <p className="text-2xl font-bold text-secondary-900">
                  {formatIDR(portfolio?.cash_available || 0)}
                </p>
              </div>
              <div className="h-12 w-12 bg-warning-100 rounded-lg flex items-center justify-center">
                <BarChart3 className="h-6 w-6 text-warning-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Positions Table */}
      <Card>
        <CardHeader>
          <CardTitle>Current Positions</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner />
            </div>
          ) : positions.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-secondary-500">No positions found</p>
              <Button
                variant="outline"
                onClick={() => setShowAddForm(true)}
                className="mt-4"
              >
                Add your first position
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-secondary-50 border-b border-secondary-200">
                  <tr>
                    <th className="text-left px-6 py-3 text-sm font-medium text-secondary-700">
                      Stock
                    </th>
                    <th className="text-right px-6 py-3 text-sm font-medium text-secondary-700">
                      Quantity
                    </th>
                    <th className="text-right px-6 py-3 text-sm font-medium text-secondary-700">
                      Avg. Price
                    </th>
                    <th className="text-right px-6 py-3 text-sm font-medium text-secondary-700">
                      Current Price
                    </th>
                    <th className="text-right px-6 py-3 text-sm font-medium text-secondary-700">
                      Market Value
                    </th>
                    <th className="text-right px-6 py-3 text-sm font-medium text-secondary-700">
                      P&L
                    </th>
                    <th className="text-right px-6 py-3 text-sm font-medium text-secondary-700">
                      P&L %
                    </th>
                    <th className="text-center px-6 py-3 text-sm font-medium text-secondary-700">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-secondary-200">
                  {positions.map((position, index) => (
                    <motion.tr
                      key={position.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="hover:bg-secondary-50 transition-colors"
                    >
                      <td className="px-6 py-4">
                        <div>
                          <div className="font-medium text-secondary-900">
                            {formatStockCode(position.stock_code)}
                          </div>
                          <div className="text-sm text-secondary-500">
                            {position.sector || 'Unknown Sector'}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right font-medium text-secondary-900">
                        {(position.quantity || 0).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-right font-medium text-secondary-900">
                        {formatIDR(position.average_price)}
                      </td>
                      <td className="px-6 py-4 text-right font-medium text-secondary-900">
                        {position.current_price ? formatIDR(position.current_price) : '-'}
                      </td>
                      <td className="px-6 py-4 text-right font-medium text-secondary-900">
                        {position.market_value ? formatIDR(position.market_value) : '-'}
                      </td>
                      <td className={`px-6 py-4 text-right font-medium ${
                        getPnLColorClass(position.unrealized_pnl || 0)
                      }`}>
                        {position.unrealized_pnl ? formatIDR(position.unrealized_pnl) : '-'}
                      </td>
                      <td className={`px-6 py-4 text-right font-medium ${
                        getPnLColorClass(position.unrealized_pnl || 0)
                      }`}>
                        {position.unrealized_pnl_percent
                          ? formatPercent(position.unrealized_pnl_percent / 100)
                          : '-'
                        }
                      </td>
                      <td className="px-6 py-4 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setEditModal({ isOpen: true, position })}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-danger-600 hover:text-danger-700"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
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

      {/* Sector Breakdown */}
      {portfolio && Object.keys(portfolio.sector_breakdown).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Sector Allocation</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(portfolio.sector_breakdown).map(([sector, percentage]) => (
                <div key={sector} className="flex items-center justify-between p-4 bg-secondary-50 rounded-lg">
                  <span className="font-medium text-secondary-900">{sector}</span>
                  <div className="text-right">
                    <div className="font-bold text-secondary-900">
                      {formatPercent(percentage / 100)}
                    </div>
                    <div className="text-sm text-secondary-600">
                      {formatIDR(totalMarketValue * (percentage / 100))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Portfolio;
