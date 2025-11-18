import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { apiClient } from '@/lib/api-complete';
import type { AIResearchReport, AuctionMarketProfile } from '@/types/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loader2 } from 'lucide-react';

const formatDate = (value: Date) => value.toISOString().slice(0, 10);

const MarketStructureInsights: React.FC = () => {
  const today = useMemo(() => new Date(), []);
  const [stockCode, setStockCode] = useState('BBCA');
  const [tradeDate, setTradeDate] = useState(formatDate(today));
  const [loadingResearch, setLoadingResearch] = useState(false);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [researchReport, setResearchReport] = useState<AIResearchReport | null>(null);
  const [amtProfile, setAmtProfile] = useState<AuctionMarketProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadAmtProfile = useCallback(async () => {
    setLoadingProfile(true);
    setError(null);
    try {
      const profiles = await apiClient.getAuctionMarketProfiles(stockCode.toUpperCase(), 1);
      setAmtProfile(profiles[0] ?? null);
    } catch (err: any) {
      setError(err?.detail || 'Failed to load auction profile');
      setAmtProfile(null);
    } finally {
      setLoadingProfile(false);
    }
  }, [stockCode]);

  useEffect(() => {
    loadAmtProfile();
  }, [loadAmtProfile]);

  const handleRunResearch = async () => {
    setLoadingResearch(true);
    setError(null);
    try {
      const report = await apiClient.runAiResearch(stockCode.toUpperCase(), {
        tradeDate,
      });
      setResearchReport(report);
    } catch (err: any) {
      setError(err?.detail || 'Failed to run research');
    } finally {
      setLoadingResearch(false);
    }
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <Card>
        <CardHeader className="flex flex-col gap-2">
          <CardTitle className="text-lg font-semibold">AI Research Console</CardTitle>
          <div className="flex flex-wrap gap-2">
            <input
              type="text"
              value={stockCode}
              onChange={(event) => setStockCode(event.target.value.toUpperCase())}
              className="border border-secondary-200 rounded-md px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
              placeholder="Ticker (e.g., BBCA)"
              maxLength={6}
            />
            <input
              type="date"
              value={tradeDate}
              max={formatDate(today)}
              onChange={(event) => setTradeDate(event.target.value)}
              className="border border-secondary-200 rounded-md px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
            />
            <Button onClick={handleRunResearch} disabled={loadingResearch}>
              {loadingResearch && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Run Research
            </Button>
          </div>
          {error && (
            <p className="text-sm text-danger-600">{error}</p>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          {researchReport ? (
            <div className="space-y-3 text-sm text-secondary-700">
              <div>
                <p className="font-medium text-secondary-900">Final Recommendation</p>
                <p className="mt-1 whitespace-pre-wrap leading-relaxed">
                  {researchReport.final_recommendation}
                </p>
                <p className="text-xs text-secondary-500 mt-1">
                  Conviction Score: {(researchReport.conviction * 100).toFixed(1)}%
                </p>
              </div>
              <div>
                <p className="font-medium text-secondary-900">Risk Manager Notes</p>
                <p className="mt-1 whitespace-pre-wrap leading-relaxed">
                  {researchReport.risk_assessment}
                </p>
              </div>
              <div>
                <p className="font-medium text-secondary-900">Debate Summary</p>
                <p className="mt-1 whitespace-pre-wrap leading-relaxed">
                  {researchReport.debate_summary}
                </p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 border-t border-secondary-100">
                {Object.entries(researchReport.analyst_notes).map(([role, note]) => (
                  <div key={role} className="bg-secondary-50 border border-secondary-100 rounded-lg p-3">
                    <p className="text-xs uppercase tracking-wide text-secondary-500 font-semibold">
                      {role}
                    </p>
                    <p className="text-sm mt-1 whitespace-pre-wrap leading-relaxed">
                      {note}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-secondary-500">
              Trigger the multi-agent research workflow to generate a narrative report for the selected stock.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold">Auction Market Profile</CardTitle>
          <Button variant="ghost" size="sm" onClick={loadAmtProfile} disabled={loadingProfile}>
            {loadingProfile && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Refresh
          </Button>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-secondary-700">
          {amtProfile ? (
            <>
              <div className="grid grid-cols-2 gap-3">
                <Metric label="Session Date" value={amtProfile.session_date} />
                <Metric label="Profile Type" value={amtProfile.profile_type || 'n/a'} />
                <Metric label="Point of Control" value={formatNumber(amtProfile.point_of_control)} />
                <Metric label="Value Area" value={`${formatNumber(amtProfile.value_area_low)} - ${formatNumber(amtProfile.value_area_high)}`} />
                <Metric label="Initial Balance" value={`${formatNumber(amtProfile.initial_balance_low)} - ${formatNumber(amtProfile.initial_balance_high)}`} />
                <Metric label="Session Range" value={formatNumber(amtProfile.session_range)} />
                <Metric label="VWAP" value={formatNumber(amtProfile.vwap)} />
                <Metric label="Total Volume" value={formatNumber(amtProfile.total_volume)} />
              </div>
              {amtProfile.single_prints && amtProfile.single_prints.length > 0 && (
                <div>
                  <p className="text-xs uppercase tracking-wide text-secondary-500 font-semibold mb-1">Single Prints</p>
                  <p className="text-sm text-secondary-700 break-words">
                    {amtProfile.single_prints.map(formatNumber).join(', ')}
                  </p>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-secondary-500">
              Auction profile will appear once intraday data is available for the selected stock.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

const formatNumber = (value?: number) => {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return 'n/a';
  }
  return Number(value).toLocaleString('en-US', { maximumFractionDigits: 2 });
};

interface MetricProps {
  label: string;
  value: string | number;
}

const Metric: React.FC<MetricProps> = ({ label, value }) => (
  <div className="bg-secondary-50 border border-secondary-100 rounded-lg p-3">
    <p className="text-xs uppercase tracking-wide text-secondary-500 font-semibold">{label}</p>
    <p className="text-sm mt-1 text-secondary-800 font-medium">{value}</p>
  </div>
);

export default MarketStructureInsights;
