import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  Trash2, 
  FileVideo, 
  Music, 
  ArrowRight, 
  Search, 
  Plus,
  ShieldCheck
} from 'lucide-react';
import { HistoryItem } from '../types/analysis';
import { getHistory, clearHistory, fetchAnalysisHistory } from '../services/api';

export const HistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [isMongoConnected, setIsMongoConnected] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    fetchAnalysisHistory(searchTerm)
      .then(({ items, mongodb_connected }) => {
        if (isMounted) {
          setHistoryItems(items);
          setIsMongoConnected(mongodb_connected);
        }
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [searchTerm]);

  const handleClear = () => {
    if (window.confirm('Are you sure you want to clear your local analysis history?')) {
      clearHistory();
      setHistoryItems([]);
    }
  };

  const filteredItems = historyItems;

  return (
    <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 space-y-8 sm:space-y-10">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-ash/80">
        <div className="space-y-1">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-pill bg-paper border border-ash text-carbon text-xs font-mono font-bold uppercase tracking-wider mb-2">
            <span className={`w-2 h-2 rounded-full ${isMongoConnected ? 'bg-mint' : 'bg-smoke'}`} />
            <span>{isMongoConnected ? 'MONGODB ATLAS CLOUD SYNCED' : 'LOCAL CACHE SYNC'}</span>
          </div>
          <h1 className="font-display text-4xl sm:text-5xl font-black uppercase tracking-tight text-carbon">
            ANALYSIS HISTORY
          </h1>
          <p className="text-xs sm:text-sm font-mono text-slate">
            {isMongoConnected
              ? 'Synchronized with MongoDB Atlas forensic repository and active learning dataset.'
              : 'Locally stored forensic reports from recent media verification sessions.'}
          </p>
        </div>

        <div className="flex items-center space-x-2.5">
          {historyItems.length > 0 && (
            <button
              type="button"
              onClick={handleClear}
              className="editorial-btn-secondary flex items-center space-x-1.5 font-mono text-xs uppercase"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear Cache</span>
            </button>
          )}

          <Link
            to="/"
            className="editorial-btn-primary flex items-center space-x-1.5 font-mono text-xs uppercase"
          >
            <Plus className="w-4 h-4" />
            <span>New Analysis</span>
          </Link>
        </div>
      </div>

      {/* Search Bar */}
      {historyItems.length > 0 && (
        <div className="relative max-w-md">
          <Search className="w-4 h-4 text-smoke absolute left-4 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by filename, hash or verdict..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-11 pr-4 py-2.5 rounded-pill bg-paper border border-ash text-xs font-mono text-carbon placeholder:text-smoke focus:outline-none focus:border-carbon transition-colors"
          />
        </div>
      )}

      {/* History List */}
      {filteredItems.length > 0 ? (
        <div className="grid grid-cols-1 gap-3.5">
          {filteredItems.map((item) => {
            const isAudioItem = item.media_type === 'AUDIO';

            return (
              <div
                key={item.id}
                onClick={() => navigate(`/results/${item.id}`, { state: { analysis: item.analysis } })}
                className="editorial-card p-5 bg-paper hover:border-carbon transition-all cursor-pointer group flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                {/* File info */}
                <div className="flex items-start space-x-4 truncate">
                  <div className="p-3 rounded-xl bg-mist border border-ash text-carbon shrink-0 group-hover:border-carbon transition-colors">
                    {isAudioItem ? <Music className="w-5 h-5" /> : <FileVideo className="w-5 h-5" />}
                  </div>
                  <div className="truncate">
                    <div className="flex items-center space-x-2">
                      <h3 className="text-sm font-bold text-carbon font-mono group-hover:underline truncate">
                        {item.filename}
                      </h3>
                      <span className="editorial-pill-tag bg-mint text-carbon border border-carbon/20 text-[10px]">
                        {item.media_type || 'VIDEO'}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 mt-1 text-[11px] font-mono text-slate">
                      <span>{item.duration_s.toFixed(1)}s</span>
                      <span>·</span>
                      <span>SHA-256: {item.sha256.slice(0, 10)}...</span>
                      <span>·</span>
                      <span>{new Date(item.created_at).toLocaleDateString()} {new Date(item.created_at).toLocaleTimeString()}</span>
                    </div>
                  </div>
                </div>

                {/* Badges & Action */}
                <div className="flex flex-wrap items-center gap-3 shrink-0">
                  
                  {/* Media risk badge */}
                  <div className="text-right font-mono">
                    <span className="text-[10px] block text-smoke uppercase">Media Risk</span>
                    <span className="editorial-pill-tag bg-mist border border-ash text-carbon text-[10px]">
                      {item.media_verdict}
                    </span>
                  </div>

                  {/* Fraud risk badge */}
                  <div className="text-right font-mono">
                    <span className="text-[10px] block text-smoke uppercase">Fraud Risk</span>
                    <span className="editorial-pill-tag bg-mist border border-ash text-carbon text-[10px]">
                      {item.fraud_level}
                    </span>
                  </div>

                  {/* Action */}
                  <div className="text-right font-mono">
                    <span className="text-[10px] block text-smoke uppercase">Action</span>
                    <span className="editorial-pill-tag bg-carbon text-paper border border-carbon text-[10px]">
                      {item.action}
                    </span>
                  </div>

                  <div className="p-2 rounded-lg bg-mist border border-ash text-carbon group-hover:bg-carbon group-hover:text-paper transition-all ml-1">
                    <ArrowRight className="w-3.5 h-3.5" />
                  </div>

                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="editorial-card-lg p-12 bg-paper text-center space-y-4">
          <div className="w-12 h-12 mx-auto rounded-full bg-mist border border-ash flex items-center justify-center text-carbon">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h3 className="font-display text-2xl font-black uppercase tracking-tight text-carbon">
            NO SESSION HISTORY
          </h3>
          <p className="text-xs font-mono text-slate max-w-sm mx-auto">
            Media analyzed in your browser session is cached locally. Analyze media to view forensic reports here.
          </p>
          <div className="pt-2">
            <Link
              to="/"
              className="editorial-btn-primary inline-flex items-center space-x-2 font-mono text-xs uppercase"
            >
              <span>Analyze Media Now</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      )}

    </div>
  );
};
