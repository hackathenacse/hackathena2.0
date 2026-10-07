import React, { useState } from 'react';
import { Download, X, Copy, Check, ExternalLink, ShieldCheck, Terminal, HelpCircle } from 'lucide-react';

interface ExtensionModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ExtensionModal: React.FC<ExtensionModalProps> = ({ isOpen, onClose }) => {
  const [copied, setCopied] = useState(false);
  const [downloaded, setDownloaded] = useState(false);

  if (!isOpen) return null;

  const handleCopyUrl = async () => {
    try {
      await navigator.clipboard.writeText('chrome://extensions');
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // Fallback
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  const handleDownload = () => {
    setDownloaded(true);
    const link = document.createElement('a');
    link.href = '/authentica-extension.zip';
    link.download = 'authentica-extension.zip';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-carbon/60 backdrop-blur-sm animate-fadeIn">
      <div 
        className="relative w-full max-w-2xl bg-paper border-2 border-carbon rounded-[28px] p-6 sm:p-8 shadow-2xl overflow-hidden max-h-[90vh] flex flex-col space-y-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-ash">
          <div className="space-y-1">
            <div className="inline-flex items-center space-x-2 px-3 py-0.5 rounded-pill bg-mint text-carbon text-xs font-mono font-bold uppercase">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>CHROME EXTENSION INSTALLER</span>
            </div>
            <h2 className="font-display text-2xl sm:text-3xl font-black uppercase tracking-tight text-carbon">
              Install Authentica on Chrome
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-full hover:bg-mist text-slate hover:text-carbon transition-colors"
            title="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="overflow-y-auto pr-1 space-y-6 flex-1 text-left">
          
          {/* Main Action Banner */}
          <div className="p-5 rounded-2xl bg-mist border border-ash flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="space-y-1 text-center sm:text-left">
              <p className="font-mono text-xs font-bold uppercase text-carbon">READY-TO-LOAD BUNDLE</p>
              <p className="text-xs text-slate">
                Download the packaged Authentica Manifest V3 Chrome Extension.
              </p>
            </div>
            <button
              type="button"
              onClick={handleDownload}
              className="editorial-btn-primary flex items-center justify-center space-x-2 shrink-0 w-full sm:w-auto text-xs uppercase"
            >
              <Download className="w-4 h-4" />
              <span>{downloaded ? 'Download Again (.zip)' : 'Download Extension (.zip)'}</span>
            </button>
          </div>

          {/* Why Developer Mode explanation */}
          <div className="p-4 rounded-xl bg-paper border border-ash text-xs text-slate font-sans flex items-start space-x-3">
            <HelpCircle className="w-4 h-4 text-carbon shrink-0 mt-0.5" />
            <p className="leading-relaxed">
              <strong>Browser Security Note:</strong> Google Chrome requires custom extensions to be added via <em>Developer Mode ("Load unpacked")</em> rather than direct silent injection. Follow the 3 quick steps below to activate it in ~10 seconds.
            </p>
          </div>

          {/* Step by step guide */}
          <div className="space-y-3">
            <p className="font-mono text-xs font-bold uppercase tracking-wider text-carbon">
              3-STEP ACTIVATION GUIDE
            </p>

            {/* Step 1 */}
            <div className="p-4 rounded-xl bg-paper border border-ash space-y-2">
              <div className="flex items-center space-x-2">
                <span className="w-5 h-5 rounded-full bg-carbon text-paper font-mono text-xs font-bold flex items-center justify-center shrink-0">1</span>
                <span className="font-mono text-xs font-bold uppercase text-carbon">Extract the ZIP Archive</span>
              </div>
              <p className="text-xs text-slate font-sans pl-7">
                After downloading, extract/unzip <code className="font-mono text-carbon bg-mist px-1.5 py-0.5 rounded">authentica-extension.zip</code> on your laptop to a folder.
              </p>
            </div>

            {/* Step 2 */}
            <div className="p-4 rounded-xl bg-paper border border-ash space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="w-5 h-5 rounded-full bg-carbon text-paper font-mono text-xs font-bold flex items-center justify-center shrink-0">2</span>
                  <span className="font-mono text-xs font-bold uppercase text-carbon">Open Chrome Extensions Page</span>
                </div>
                <button
                  type="button"
                  onClick={handleCopyUrl}
                  className="px-2.5 py-1 rounded-pill bg-mist border border-ash hover:border-carbon text-[11px] font-mono text-carbon flex items-center space-x-1.5 transition-all"
                >
                  {copied ? (
                    <>
                      <Check className="w-3 h-3 text-emerald-600" />
                      <span className="text-emerald-700 font-bold">Copied URL!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3 text-slate" />
                      <span>Copy chrome://extensions</span>
                    </>
                  )}
                </button>
              </div>
              <p className="text-xs text-slate font-sans pl-7">
                Paste <code className="font-mono text-carbon bg-mist px-1.5 py-0.5 rounded">chrome://extensions</code> into your Chrome address bar and hit Enter.
              </p>
            </div>

            {/* Step 3 */}
            <div className="p-4 rounded-xl bg-paper border border-ash space-y-2">
              <div className="flex items-center space-x-2">
                <span className="w-5 h-5 rounded-full bg-carbon text-paper font-mono text-xs font-bold flex items-center justify-center shrink-0">3</span>
                <span className="font-mono text-xs font-bold uppercase text-carbon">Turn on Developer Mode & Load Unpacked</span>
              </div>
              <p className="text-xs text-slate font-sans pl-7 leading-relaxed">
                Toggle <strong className="text-carbon">"Developer mode"</strong> in the top-right corner of Chrome, then click the <strong className="text-carbon">"Load unpacked"</strong> button in the top-left and select your extracted extension folder.
              </p>
            </div>

          </div>

          {/* Success checklist banner */}
          <div className="p-4 rounded-2xl bg-carbon text-paper font-mono text-xs space-y-2">
            <div className="flex items-center space-x-2 text-mint font-bold uppercase">
              <Terminal className="w-4 h-4" />
              <span>LIVE MEDIA CAPTURE READY</span>
            </div>
            <p className="text-smoke text-[11px] font-sans leading-relaxed">
              Once loaded, pin Authentica to your Chrome toolbar. You can now scan active video calls, YouTube clips, or Google Meet sessions directly for synthetic deepfakes and fraud.
            </p>
          </div>

        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-ash flex items-center justify-end">
          <button
            type="button"
            onClick={onClose}
            className="editorial-btn-secondary text-xs uppercase"
          >
            Done
          </button>
        </div>

      </div>
    </div>
  );
};

