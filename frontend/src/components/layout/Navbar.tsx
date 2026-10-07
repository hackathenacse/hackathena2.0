import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Puzzle, Download } from 'lucide-react';
import { ExtensionModal } from '../ExtensionModal';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const [isExtensionModalOpen, setIsExtensionModalOpen] = useState(false);

  const isActive = (path: string) => location.pathname === path;

  return (
    <>
      <header className="sticky top-4 z-40 px-4 sm:px-6 lg:px-8 mb-6 sm:mb-8">
        <div className="max-w-[1200px] mx-auto">
          <div className="bg-paper border border-ash rounded-pill px-5 sm:px-6 py-2.5 sm:py-3 flex items-center justify-between shadow-none transition-all">
            
            {/* Logo & Brand */}
            <Link to="/" className="flex items-center space-x-2 group">
              <span className="font-display text-xl sm:text-2xl font-black uppercase tracking-tight text-carbon">
                AUTHENTICA
              </span>
            </Link>

            {/* Navigation Links + Extension Button */}
            <nav className="flex items-center space-x-1 sm:space-x-1.5">
              <Link
                to="/"
                className={`px-3.5 sm:px-4 py-1.5 rounded-pill text-xs font-mono font-bold uppercase transition-all ${
                  isActive('/')
                    ? 'bg-carbon text-paper'
                    : 'text-slate hover:text-carbon hover:bg-mist'
                }`}
              >
                Analyze
              </Link>

              <Link
                to="/history"
                className={`px-3.5 sm:px-4 py-1.5 rounded-pill text-xs font-mono font-bold uppercase transition-all ${
                  isActive('/history')
                    ? 'bg-carbon text-paper'
                    : 'text-slate hover:text-carbon hover:bg-mist'
                }`}
              >
                History
              </Link>

              <Link
                to="/awareness"
                className={`px-3.5 sm:px-4 py-1.5 rounded-pill text-xs font-mono font-bold uppercase transition-all ${
                  isActive('/awareness')
                    ? 'bg-carbon text-paper'
                    : 'text-slate hover:text-carbon hover:bg-mist'
                }`}
              >
                Awareness
              </Link>

              {/* Install Extension Button */}
              <button
                type="button"
                onClick={() => setIsExtensionModalOpen(true)}
                className="ml-1 sm:ml-2 px-3 sm:px-3.5 py-1.5 rounded-pill bg-mist border border-ash hover:border-carbon hover:bg-paper text-carbon text-xs font-mono font-bold uppercase transition-all flex items-center space-x-1.5 group"
                title="Download Authentica Chrome Extension"
              >
                <Puzzle className="w-3.5 h-3.5 text-carbon group-hover:rotate-12 transition-transform" />
                <span className="hidden sm:inline">Extension</span>
                <Download className="w-3 h-3 text-slate group-hover:text-carbon" />
              </button>
            </nav>

          </div>
        </div>
      </header>

      {/* Extension Install Modal */}
      <ExtensionModal
        isOpen={isExtensionModalOpen}
        onClose={() => setIsExtensionModalOpen(false)}
      />
    </>
  );
};

