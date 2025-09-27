import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  AlertTriangle,
  TrendingDown,
  Shield,
  BarChart3,
  Activity,
  Target,
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
} from '@/lib/utils';

const Risk: React.FC = () => {
  const { riskOverview, fetchRiskOverview, portfolio, isLoading } = useDashboardStore();

  useEffect(() => {
    fetchRiskOverview();
  }, [fetchRiskOverview]);

  const getRiskLevelColor = (level: string) => {
    switch (level?.toLowerCase()) {
      case 'low': return 'text-success-600 bg-success-100';
      case 'medium': return 'text-warning-600 bg-warning-100';
      case 'high': return 'text-danger-600 bg-danger-100';
      default: return 'text-secondary-600 bg-secondary-100';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-secondary-900 mb-2">
            Risk Monitoring
          </h1>
          <p className="text-secondary-600">
            Monitor portfolio risk metrics and exposure analysis
          </p>
        </div>

        <Button className="flex items-center gap-2">
          <Activity className="h-4 w-4" />
          Risk Report
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner />
        </div>
      ) : (
        <>
          {/* Risk Overview Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-secondary-600">Overall Risk</p>
                    <Badge className={`mt-2 ${getRiskLevelColor(riskOverview?.overall_risk_level || 'Medium')}`}>
                      {riskOverview?.overall_risk_level || 'Medium'}
                    </Badge>
                  </div>
                  <div className="h-12 w-12 bg-warning-100 rounded-lg flex items-center justify-center">
                    <AlertTriangle className="h-6 w-6 text-warning-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-secondary-600">Value at Risk</p>
                    <p className="text-2xl font-bold text-danger-600">
                      {formatIDR(riskOverview?.value_at_risk || 25000000)}
                    </p>
                    <p className="text-xs text-secondary-500 mt-1">95% confidence</p>
                  </div>
                  <div className="h-12 w-12 bg-danger-100 rounded-lg flex items-center justify-center">
                    <TrendingDown className="h-6 w-6 text-danger-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-secondary-600">Portfolio Beta</p>
                    <p className="text-2xl font-bold text-secondary-900">
                      {riskOverview?.beta || '1.12'}
                    </p>
                    <p className="text-xs text-secondary-500 mt-1">vs IDX Composite</p>
                  </div>
                  <div className="h-12 w-12 bg-info-100 rounded-lg flex items-center justify-center">
                    <BarChart3 className="h-6 w-6 text-info-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-secondary-600">Diversification</p>
                    <p className="text-2xl font-bold text-success-600">
                      {formatPercent(riskOverview?.diversification_score / 100 || 0.78)}
                    </p>
                    <p className="text-xs text-secondary-500 mt-1">Sector spread</p>
                  </div>
                  <div className="h-12 w-12 bg-success-100 rounded-lg flex items-center justify-center">
                    <Shield className="h-6 w-6 text-success-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Risk Breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Position Risk Analysis */}
            <Card>
              <CardHeader>
                <CardTitle>Position Risk Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {riskOverview?.position_risks?.length > 0 ? (
                    riskOverview.position_risks.map((position: any, index: number) => (
                      <motion.div
                        key={position.stock_code}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="flex items-center justify-between p-4 bg-secondary-50 rounded-lg"
                      >
                        <div>
                          <p className="font-medium text-secondary-900">{position.stock_code}</p>
                          <p className="text-sm text-secondary-600">
                            {formatPercent(position.portfolio_weight / 100)} of portfolio
                          </p>
                        </div>
                        <div className="text-right">
                          <Badge className={getRiskLevelColor(position.risk_level)}>
                            {position.risk_level}
                          </Badge>
                          <p className="text-sm text-secondary-600 mt-1">
                            Volatility: {formatPercent(position.volatility / 100)}
                          </p>
                        </div>
                      </motion.div>
                    ))
                  ) : (
                    <div className="text-center py-8">
                      <Target className="h-12 w-12 text-secondary-400 mx-auto mb-4" />
                      <p className="text-secondary-500">Loading risk analysis...</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Risk Metrics */}
            <Card>
              <CardHeader>
                <CardTitle>Risk Metrics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  <div className="flex justify-between items-center">
                    <span className="text-secondary-700">Maximum Drawdown</span>
                    <span className="font-medium text-danger-600">
                      {formatPercent(riskOverview?.max_drawdown / 100 || -0.15)}
                    </span>
                  </div>

                  <div className="flex justify-between items-center">
                    <span className="text-secondary-700">Sharpe Ratio</span>
                    <span className="font-medium text-secondary-900">
                      {riskOverview?.sharpe_ratio || '1.45'}
                    </span>
                  </div>

                  <div className="flex justify-between items-center">
                    <span className="text-secondary-700">Portfolio Volatility</span>
                    <span className="font-medium text-warning-600">
                      {formatPercent(riskOverview?.volatility / 100 || 0.18)}
                    </span>
                  </div>

                  <div className="flex justify-between items-center">
                    <span className="text-secondary-700">Correlation with IDX</span>
                    <span className="font-medium text-secondary-900">
                      {riskOverview?.correlation || '0.85'}
                    </span>
                  </div>

                  <hr className="border-secondary-200" />

                  <div className="flex justify-between items-center">
                    <span className="text-secondary-700">Last Updated</span>
                    <span className="text-sm text-secondary-500">
                      {riskOverview?.last_updated
                        ? formatWIBDateTime(riskOverview.last_updated)
                        : 'Just now'
                      }
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sector Exposure */}
          {portfolio?.sector_breakdown && Object.keys(portfolio.sector_breakdown).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Sector Risk Exposure</CardTitle>
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
                          {formatIDR((portfolio?.total_market_value || 0) * (percentage / 100))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
};

export default Risk;