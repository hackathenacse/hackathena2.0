import React, { useState } from 'react';
import { 
  KeyRound, 
  Smartphone, 
  Lock, 
  Headphones,
  Check,
  X,
  RotateCcw
} from 'lucide-react';

interface QuizQuestion {
  id: number;
  scenario: string;
  options: { text: string; isCorrect: boolean; explanation: string }[];
}

const QUIZ_QUESTIONS: QuizQuestion[] = [
  {
    id: 1,
    scenario: "You receive a video message on WhatsApp from your CEO asking you to urgently wire ₹500,000 to a new vendor account and keep it strictly confidential. The video matches their face and voice.",
    options: [
      { 
        text: "Execute the wire transfer immediately since the video looks genuine.", 
        isCorrect: false, 
        explanation: "Generative AI face-swapping and voice-cloning tools can produce convincing executive deepfakes. Urgent secrecy is a signature red flag." 
      },
      { 
        text: "Pause action and verify via an out-of-band call to their known corporate number.", 
        isCorrect: true, 
        explanation: "Correct. Never rely on the incoming communication channel. Always initiate a secondary out-of-band verification." 
      },
      { 
        text: "Reply in the WhatsApp chat asking them to confirm.", 
        isCorrect: false, 
        explanation: "If the sender's account was compromised or spoofed, the scammer will simply reply confirming the request." 
      }
    ]
  },
  {
    id: 2,
    scenario: "Your bank's fraud department calls stating that an unauthorized transaction was blocked. They ask you to read out the 6-digit SMS verification code you just received to cancel it.",
    options: [
      { 
        text: "Read the code immediately to stop the fraudulent transaction.", 
        isCorrect: false, 
        explanation: "Banks NEVER ask for 2FA OTP codes. The scammer is attempting to log into your account and needs the OTP to bypass security." 
      },
      { 
        text: "Hang up immediately and call the official bank phone number on your debit card.", 
        isCorrect: true, 
        explanation: "Correct. OTP extraction is a direct credential theft attack. Legitimate bank representatives will never ask for your SMS code." 
      },
      { 
        text: "Ask the caller for their badge ID and give them the first 3 digits.", 
        isCorrect: false, 
        explanation: "Scammers frequently invent plausible employee numbers. Never share any part of an authentication code." 
      }
    ]
  },
  {
    id: 3,
    scenario: "A friend calls with a distressed voice saying they were in a car crash in another city and urgently need crypto/gift card money for hospital bail.",
    options: [
      { 
        text: "Transfer the money right away since their voice tone sounded anxious.", 
        isCorrect: false, 
        explanation: "AI voice cloning models can mimic emotional tone and distress from a 3-second social media audio sample." 
      },
      { 
        text: "Ask a pre-agreed family safe word or call mutual relatives to confirm.", 
        isCorrect: true, 
        explanation: "Correct. Pre-agreed safe words or contacting family members on standard numbers immediately disarms voice cloning attacks." 
      }
    ]
  }
];

export const AwarenessPage: React.FC = () => {
  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, number>>({});
  const [showResults, setShowResults] = useState<Record<number, boolean>>({});

  const handleSelectOption = (questionId: number, optionIdx: number) => {
    setSelectedAnswers(prev => ({ ...prev, [questionId]: optionIdx }));
    setShowResults(prev => ({ ...prev, [questionId]: true }));
  };

  const handleResetQuiz = () => {
    setSelectedAnswers({});
    setShowResults({});
  };

  return (
    <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 space-y-12 sm:space-y-16">
      
      {/* 1. Header Hero */}
      <div className="space-y-4 pt-2 sm:pt-4">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-pill bg-paper border border-ash text-carbon text-xs font-mono font-bold uppercase tracking-wider">
          <span>SECURITY &amp; FRAUD DEFENSE PUBLICATION</span>
        </div>

        <h1 className="font-display text-6xl sm:text-7xl lg:text-8xl font-black uppercase tracking-tight leading-[0.88] text-carbon">
          KNOW THE<br />
          ATTACK.
        </h1>

        <p className="text-base sm:text-lg text-slate leading-relaxed max-w-2xl font-normal">
          Generative AI tools enable synthetic impersonation at zero marginal cost. Learn the primary attack vectors, psychological pressure patterns, and defense protocols.
        </p>
      </div>

      {/* 2. Inverted Black Principle Block */}
      <div className="editorial-inverted-card p-8 sm:p-12 space-y-6">
        <div className="flex items-center justify-between font-mono text-xs text-smoke pb-4 border-b border-graphite">
          <span className="text-mint font-bold uppercase tracking-wider">THE GOLDEN DEFENSE RULE</span>
          <span>ORTHOGONAL EVALUATION</span>
        </div>

        <h2 className="font-display text-3xl sm:text-4xl lg:text-5xl font-black uppercase tracking-tight text-paper">
          MEDIA RISK ≠ FRAUD RISK
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
          <div className="p-6 rounded-[24px] bg-graphite/60 border border-graphite space-y-2">
            <span className="font-mono text-xs font-bold text-mint uppercase">01 / MEDIA MANIPULATION</span>
            <p className="text-xs sm:text-sm text-smoke leading-relaxed font-sans">
              Measures synthetic face swaps, GAN neural artifacts, and voice synthesis. A video can be completely AI-generated without harmful intent (e.g. parody, creative CGI).
            </p>
          </div>

          <div className="p-6 rounded-[24px] bg-graphite/60 border border-graphite space-y-2">
            <span className="font-mono text-xs font-bold text-mint uppercase">02 / FRAUD INTENT</span>
            <p className="text-xs sm:text-sm text-smoke leading-relaxed font-sans">
              Measures psychological extortion directives (OTP theft, wire demands, remote software). Authentic footage of real people can still be weaponized in scams.
            </p>
          </div>
        </div>
      </div>

      {/* 3. Real-World Attack Case Studies */}
      <div className="space-y-6">
        <div className="pb-3 border-b border-ash/80">
          <span className="font-mono text-xs font-bold uppercase text-slate">REAL-WORLD ATTACK VECTORS</span>
          <h2 className="font-display text-3xl sm:text-4xl font-black uppercase tracking-tight text-carbon mt-1">
            HOW SCAMMERS OPERATE
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* Case 1 */}
          <div className="editorial-card p-6 sm:p-8 bg-paper space-y-4">
            <div className="flex items-center justify-between">
              <span className="editorial-pill-tag bg-mist border border-ash text-carbon">CASE 01</span>
              <KeyRound className="w-5 h-5 text-carbon" />
            </div>
            <h3 className="font-display text-2xl font-bold uppercase tracking-tight text-carbon">
              CEO &amp; Executive Wire Fraud
            </h3>
            <p className="text-xs sm:text-sm text-slate leading-relaxed font-sans">
              Synthetic video or voice note impersonating an executive requesting an urgent, confidential wire transfer to an unverified vendor account.
            </p>
            <div className="p-3 rounded-xl bg-mist font-mono text-xs text-slate border border-ash/60">
              <strong>Signature Red Flag:</strong> "Keep this between us until the deal closes."
            </div>
          </div>

          {/* Case 2 */}
          <div className="editorial-card p-6 sm:p-8 bg-paper space-y-4">
            <div className="flex items-center justify-between">
              <span className="editorial-pill-tag bg-mist border border-ash text-carbon">CASE 02</span>
              <Headphones className="w-5 h-5 text-carbon" />
            </div>
            <h3 className="font-display text-2xl font-bold uppercase tracking-tight text-carbon">
              Family Emergency Voice Cloning
            </h3>
            <p className="text-xs sm:text-sm text-slate leading-relaxed font-sans">
              Cloned audio of a family member claiming an accident or arrest, demanding immediate cryptocurrency, wire transfer, or gift card bail.
            </p>
            <div className="p-3 rounded-xl bg-mist font-mono text-xs text-slate border border-ash/60">
              <strong>Signature Red Flag:</strong> Emotional panic paired with immediate untraceable payment demands.
            </div>
          </div>

          {/* Case 3 */}
          <div className="editorial-card p-6 sm:p-8 bg-paper space-y-4">
            <div className="flex items-center justify-between">
              <span className="editorial-pill-tag bg-mist border border-ash text-carbon">CASE 03</span>
              <Smartphone className="w-5 h-5 text-carbon" />
            </div>
            <h3 className="font-display text-2xl font-bold uppercase tracking-tight text-carbon">
              Remote Desktop Takeover
            </h3>
            <p className="text-xs sm:text-sm text-slate leading-relaxed font-sans">
              Impersonators claiming to be IT support or bank security instructing victims to install AnyDesk, TeamViewer, or QuickSupport.
            </p>
            <div className="p-3 rounded-xl bg-mist font-mono text-xs text-slate border border-ash/60">
              <strong>Signature Red Flag:</strong> Direct instructions to grant unattended remote access.
            </div>
          </div>

          {/* Case 4 */}
          <div className="editorial-card p-6 sm:p-8 bg-paper space-y-4">
            <div className="flex items-center justify-between">
              <span className="editorial-pill-tag bg-mist border border-ash text-carbon">CASE 04</span>
              <Lock className="w-5 h-5 text-carbon" />
            </div>
            <h3 className="font-display text-2xl font-bold uppercase tracking-tight text-carbon">
              2FA / OTP Interception
            </h3>
            <p className="text-xs sm:text-sm text-slate leading-relaxed font-sans">
              Callers pretending to cancel an unauthorized transaction by asking you to read out the verification code received on your phone.
            </p>
            <div className="p-3 rounded-xl bg-mist font-mono text-xs text-slate border border-ash/60">
              <strong>Signature Red Flag:</strong> Any request to verbalize or paste an SMS security code.
            </div>
          </div>

        </div>
      </div>

      {/* 4. Interactive Security Quiz */}
      <div className="editorial-card-lg p-8 sm:p-12 bg-paper space-y-8 border border-ash">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-ash/80">
          <div>
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-pill bg-mint text-carbon text-xs font-mono font-bold uppercase tracking-wider mb-2">
              <span>INTERACTIVE ASSESSMENT</span>
            </div>
            <h2 className="font-display text-3xl sm:text-4xl lg:text-5xl font-black uppercase tracking-tight text-carbon">
              CAN YOU SPOT THE SCAM?
            </h2>
          </div>
          <button
            type="button"
            onClick={handleResetQuiz}
            className="editorial-btn-secondary flex items-center space-x-2 font-mono text-xs uppercase"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Quiz</span>
          </button>
        </div>

        <div className="space-y-8">
          {QUIZ_QUESTIONS.map((q, qIdx) => {
            const isAnswered = showResults[q.id];
            const selectedIdx = selectedAnswers[q.id];

            return (
              <div key={q.id} className="p-6 rounded-[24px] bg-mist border border-ash/80 space-y-4">
                <div className="flex items-center justify-between font-mono text-xs text-slate">
                  <span className="font-bold text-carbon uppercase">QUESTION 0{qIdx + 1}</span>
                  <span className="text-smoke">SCENARIO ANALYSIS</span>
                </div>

                <p className="text-sm sm:text-base font-bold text-carbon font-sans leading-relaxed">
                  "{q.scenario}"
                </p>

                <div className="space-y-2.5 pt-2">
                  {q.options.map((opt, optIdx) => {
                    const isSelected = selectedIdx === optIdx;
                    let optionStyle = "bg-paper border-ash text-carbon hover:border-carbon";

                    if (isAnswered) {
                      if (opt.isCorrect) {
                        optionStyle = "bg-mint border-carbon text-carbon font-semibold";
                      } else if (isSelected && !opt.isCorrect) {
                        optionStyle = "bg-paper border-carbon text-carbon line-through opacity-70";
                      } else {
                        optionStyle = "bg-paper/50 border-ash/50 text-smoke";
                      }
                    }

                    return (
                      <button
                        key={optIdx}
                        type="button"
                        onClick={() => handleSelectOption(q.id, optIdx)}
                        className={`w-full p-4 rounded-xl border text-left text-xs sm:text-sm font-sans transition-all flex items-start justify-between gap-3 ${optionStyle}`}
                      >
                        <span>{opt.text}</span>
                        {isAnswered && opt.isCorrect && (
                          <Check className="w-4 h-4 text-carbon shrink-0 mt-0.5" />
                        )}
                        {isAnswered && isSelected && !opt.isCorrect && (
                          <X className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                        )}
                      </button>
                    );
                  })}
                </div>

                {isAnswered && (
                  <div className="p-4 rounded-xl bg-paper border border-carbon text-xs font-mono space-y-1">
                    <p className="font-bold text-carbon">
                      {q.options[selectedIdx].isCorrect ? "CORRECT ASSESSMENT ✓" : "CRITICAL RISK IDENTIFIED ⚠️"}
                    </p>
                    <p className="text-slate font-sans">
                      {q.options[selectedIdx].explanation}
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 5. 3-Step Verification Protocol */}
      <div className="editorial-inverted-card p-8 sm:p-12 space-y-6">
        <div className="pb-4 border-b border-graphite">
          <span className="editorial-pill-tag bg-graphite text-mint text-xs font-mono font-bold mb-2">
            OFFICIAL SECURITY CHECKLIST
          </span>
          <h2 className="font-display text-3xl sm:text-4xl font-black uppercase tracking-tight text-paper">
            THE 3-STEP "STOP AND VERIFY" PROTOCOL
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 font-sans">
          <div className="p-6 rounded-[24px] bg-graphite/60 border border-graphite space-y-2">
            <span className="font-mono text-xs font-bold text-mint">STEP 01</span>
            <p className="font-bold text-paper font-mono">PAUSE ACTION</p>
            <p className="text-xs text-smoke leading-relaxed">
              Never execute transactions or share credentials during an unverified incoming message or call.
            </p>
          </div>
          <div className="p-6 rounded-[24px] bg-graphite/60 border border-graphite space-y-2">
            <span className="font-mono text-xs font-bold text-mint">STEP 02</span>
            <p className="font-bold text-paper font-mono">OUT-OF-BAND CALL</p>
            <p className="text-xs text-smoke leading-relaxed">
              Initiate a new communication on known corporate directory phone numbers.
            </p>
          </div>
          <div className="p-6 rounded-[24px] bg-graphite/60 border border-graphite space-y-2">
            <span className="font-mono text-xs font-bold text-mint">STEP 03</span>
            <p className="font-bold text-paper font-mono">PRE-AGREED PASSPHRASE</p>
            <p className="text-xs text-smoke leading-relaxed">
              Establish a private family or corporate verification code that AI voice clones cannot predict.
            </p>
          </div>
        </div>
      </div>

    </div>
  );
};
