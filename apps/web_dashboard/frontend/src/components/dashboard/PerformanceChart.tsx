import React, { useRef } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import 'chartjs-adapter-date-fns';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { useDashboardStore } from '@/store/dashboard';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { formatIDR, formatPercent } from '@/lib/utils';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
);

interface PerformanceData {
  date: string;
  portfolioValue: number;
  pnl: number;
  cumulativeReturn: number;
}

const PerformanceChart: React.FC = () => {
  const { performanceAnalytics, portfolio, isLoading } = useDashboardStore();
  const chartRef = useRef<ChartJS<'line', any, string>>(null);

  // Generate sample performance data (in real app, this would come from API)
  const generatePerformanceData = (): PerformanceData[] => {
    const data: PerformanceData[] = [];
    const baseValue = portfolio?.total_cost_basis || 1000000000; // 1B IDR default
    const days = 30;
    const now = new Date();

    for (let i = days; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      
      // Simulate realistic market movements
      const volatility = 0.02; // 2% daily volatility
      const trend = 0.0003; // Slight upward trend
      const randomChange = (Math.random() - 0.5) * volatility + trend;
      const dayReturn = i === days ? 0 : randomChange;
      
      const portfolioValue = i === 0 ? baseValue : 
        data[data.length - 1]?.portfolioValue * (1 + dayReturn) || baseValue;
      
      const pnl = portfolioValue - baseValue;
      const cumulativeReturn = (portfolioValue - baseValue) / baseValue;
      
      data.push({
        date: date.toISOString().split('T')[0],
        portfolioValue,
        pnl,
        cumulativeReturn,
      });
    }

    return data;
  };

  const performanceData = generatePerformanceData();
  const latestReturn = performanceData[performanceData.length - 1]?.cumulativeReturn || 0;

  const chartData = {
    labels: performanceData.map(d => d.date),
    datasets: [
      {
        label: 'Portfolio Value',
        data: performanceData.map(d => d.portfolioValue),
        borderColor: latestReturn >= 0 ? 'rgb(34, 197, 94)' : 'rgb(239, 68, 68)',
        backgroundColor: latestReturn >= 0 ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.1,
        pointRadius: 0,
        pointHoverRadius: 4,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: 'white',
        bodyColor: 'white',
        borderColor: 'rgba(255, 255, 255, 0.2)',
        borderWidth: 1,
        callbacks: {
          label: function(context: any) {
            const value = context.parsed.y;
            const dataPoint = performanceData[context.dataIndex];
            return [
              `Value: ${formatIDR(value)}`,
              `P&L: ${formatIDR(dataPoint.pnl)}`,
              `Return: ${formatPercent(dataPoint.cumulativeReturn)}`,
            ];
          },
        },
      },
    },
    scales: {
      x: {
        type: 'time' as const,
        time: {
          unit: 'day' as const,
          displayFormats: {
            day: 'MMM dd',
          },
        },
        grid: {
          display: false,
        },
        ticks: {
          color: 'rgb(107, 114, 128)',
          maxTicksLimit: 6,
        },
      },
      y: {
        grid: {
          color: 'rgba(107, 114, 128, 0.1)',
        },
        ticks: {
          color: 'rgb(107, 114, 128)',
          callback: function(value: any) {
            return formatIDR(value, true); // Abbreviated format
          },
        },
      },
    },
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    elements: {
      point: {
        hoverBackgroundColor: 'white',
        hoverBorderWidth: 2,
      },
    },
  };

  if (isLoading && !portfolio) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Portfolio Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-64">
            <LoadingSpinner />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Portfolio Performance</span>
          <div className="text-right">
            <div className={`text-sm font-medium ${
              latestReturn >= 0 ? 'text-success-600' : 'text-danger-600'
            }`}>
              {formatPercent(latestReturn)}
            </div>
            <div className="text-xs text-secondary-500">30 days</div>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <Line ref={chartRef} data={chartData} options={chartOptions} />
        </div>
        
        {/* Performance Metrics */}
        <div className="mt-4 grid grid-cols-3 gap-3 pt-3 border-t border-secondary-200">
          <div className="text-center p-2 rounded-lg bg-secondary-50">
            <p className="text-xs text-secondary-500 mb-1">Volatility</p>
            <p className="text-sm font-semibold text-secondary-900">
              {performanceAnalytics?.performance_metrics?.volatility
                ? formatPercent(performanceAnalytics.performance_metrics.volatility)
                : '2.1%'}
            </p>
          </div>
          <div className="text-center p-2 rounded-lg bg-secondary-50">
            <p className="text-xs text-secondary-500 mb-1">Sharpe Ratio</p>
            <p className="text-sm font-semibold text-secondary-900">
              {performanceAnalytics?.performance_metrics?.sharpe_ratio?.toFixed(2) || '1.42'}
            </p>
          </div>
          <div className="text-center p-2 rounded-lg bg-secondary-50">
            <p className="text-xs text-secondary-500 mb-1">Max Drawdown</p>
            <p className="text-sm font-semibold text-danger-600">
              {performanceAnalytics?.performance_metrics?.max_drawdown
                ? formatPercent(performanceAnalytics.performance_metrics.max_drawdown)
                : '-4.2%'}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default PerformanceChart;
