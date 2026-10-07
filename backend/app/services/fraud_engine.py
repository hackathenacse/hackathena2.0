import logging
import re
from typing import List, Optional, Tuple

from app.schemas.analysis import SpeechResult, SpeechSegment
from app.schemas.fraud import (
    FraudCategoryEvidence,
    FraudEvidenceItem,
    FraudRequestedAction,
    FraudResult,
)

logger = logging.getLogger("authentica")


class FraudIntentEngine:
    """
    Stage 3 — Fraud Intent Engine.
    Performs deterministic, rule-based social-engineering and fraud signal extraction
    from timestamped Whisper transcript segments.
    """

    # Category regex patterns with contextual precision (financial words alone do not trigger PAYMENT_CREDENTIAL)
    CATEGORY_PATTERNS = {
        "AUTHORITY": [
            (r"\b(?:i am|this is|speaking as)\s+(?:the\s+|your\s+|our\s+|an?\s+)?(?:project\s+|senior\s+|general\s+|regional\s+|acting\s+)?(?:ceo|cfo|executive|director|manager|boss|chief|president)\b", "Executive or organizational authority claim"),
            (r"\b(?:police|fbi|cia|interpol|sheriff|detective|officer|marshal|law enforcement|federal agent)\b", "Law enforcement authority claim"),
            (r"\b(?:irs|tax department|revenue service|customs|court|judge|legal department|attorney general)\b", "Government/legal authority claim"),
            (r"\b(?:bank manager|security department|fraud department|technical support|it support|helpdesk)\b", "Institutional security/support authority claim"),
        ],
        "URGENCY": [
            (r"\b(?:immediately|right now|urgently|hurry|asap|without delay|at once)\b", "Immediate urgency directive"),
            (r"\b(?:within\s+\d+\s+(?:minutes?|hours?)|before\s+it(?:'s|\s+is)\s+too\s+late|time\s+is\s+running\s+out)\b", "Critical time deadline pressure"),
            (r"\b(?:account\s+will\s+be\s+blocked|funds\s+frozen|suspended\s+today|critical\s+deadline)\b", "Impending account suspension/block pressure"),
        ],
        "PAYMENT_CREDENTIAL": [
            # Direct payment directives (financial words alone do NOT match)
            (r"\b(?:please\s+)?(?:send|transfer|wire|pay|deposit|remit|give|share)\s+(?:me\s+|us\s+)?(?:the\s+|this\s+|my\s+|our\s+|to\s+(?:the|this|my|our)\s+)?\s*(?:funds|money|cash|[\$₹€£]|\d+)\b", "Directed financial payment demand"),
            (r"\b(?:i\s+need\s+you\s+to|you\s+(?:must|need\s+to|have\s+to))\s+(?:send|transfer|wire|pay|deposit|give)\s+(?:me\s+|us\s+)?(?:the\s+|this\s+|my\s+|our\s+)?\s*(?:funds|money|cash|[\$₹€£]|\d+)\b", "Direct order to transfer funds"),
            (r"\b(?:can\s+you|could\s+you)\s+(?:send|transfer|wire|pay|deposit|give)\s+(?:me\s+|us\s+)?(?:the\s+|this\s+|my\s+|our\s+)?\s*(?:money|funds|cash|[\$₹€£]|\d+)\b", "Directed financial payment request"),
            (r"\b(?:send|transfer|wire|give)\s+(?:me\s+)?(?:[₹\$€£]|\d+[\d,]*\s*(?:rupees|dollars|inr|usd|cash|funds|money))\b", "Specific monetary amount extraction request"),
            (r"\b(?:transfer\s+funds\s+immediately|wire\s+the\s+funds|transfer\s+to\s+the\s+new\s+account)\b", "Explicit fund transfer instruction"),
            # Credential extraction
            (r"\b(?:share|give|tell|send|provide|read\s+out)\s+(?:.*?\b)?(?:otp|passcode|password|pin|cvv|credentials|bank\s+details|card\s+number)\b", "Direct credential/OTP extraction demand"),
            (r"\b(?:one[- ]time\s+pass(?:code|word)?|2fa\s+code|verification\s+code|security\s+code)\b", "Authentication token/OTP reference"),
            # Shady payment mechanisms
            (r"\b(?:apple\s+gift\s*cards?|google\s+play\s*cards?|vanilla\s*visa|western\s+union|moneygram)\b", "Untraceable gift card/remittance demand"),
            (r"\b(?:buy\s+gift\s*cards|pay\s+in\s+bitcoin|pay\s+with\s+crypto|transfer\s+usdt)\b", "Crypto/gift card payment demand"),
            # Routing changes
            (r"\b(?:update|change)\s+(?:the\s+)?(?:bank|invoice|beneficiary|routing)\s+(?:details|number|destination|account)\b", "Payment beneficiary account modification"),
        ],
        "SECRECY": [
            (r"\b(?:don'?t|do\s+not|never)\s+(?:\w+\s+){0,3}(?:tell|inform|contact|call|notify|alert)\s+(?:anyone|the\s+police|police|authorities|cops|family|friends|anyone\s+else)\b", "Directive not to contact police or authorities"),
            (r"\b(?:don'?t\s+(?:\w+\s+){0,2}tell|keep\s+this\s+(?:between\s+us|confidential|secret|private|quiet))\b", "Demand for secrecy or non-disclosure"),
            (r"\b(?:do\s+not\s+(?:call|contact|mention|discuss|inform)\s+(?:anyone|the\s+police|authorities|the\s+office|colleagues|family|boss))\b", "Instruction to isolate victim from advisors or authorities"),
            (r"\b(?:off\s+the\s+record|strictly\s+confidential|top\s+secret|between\s+you\s+and\s+me)\b", "Claim of confidential/secret dealing"),
            (r"\b(?:not\s+a\s+word|keep\s+(?:quiet|silent|your\s+mouth\s+shut))\b", "Demand for silence"),
        ],
        "CHANNEL_IDENTITY_CHANGE": [
            (r"\b(?:lost\s+(?:my\s+)?(?:phone|access)|new\s+(?:temporary\s+)?(?:number|phone)|using\s+a\s+different\s+phone)\b", "Claim of lost phone or temporary number"),
            (r"\b(?:text\s+me\s+on\s+whatsapp|message\s+me\s+on\s+telegram|this\s+is\s+my\s+personal\s+(?:number|cell))\b", "Diversion to personal/unmonitored messaging app"),
            (r"\b(?:changed\s+my\s+number|reach\s+me\s+here\s+instead)\b", "Out-of-band communication switch"),
        ],
        "THREAT_PRESSURE": [
            # Direct physical threats, killing, harm, hostage, ransom
            (r"\b(?:i\s+will|i'll|we\s+will|we'll|going\s+to)\s+(?:kill|hurt|harm|shoot|murder|beat|injure|destroy|ruin)\s+(?:him|her|them|you|your\s+\w+)\b", "Direct threat of death or physical harm"),
            (r"\b(?:will\s+kill\s+(?:him|her|them|you)|will\s+hurt\s+(?:him|her|them|you)|will\s+shoot\s+(?:him|her|them|you)|will\s+harm\s+(?:him|her|them|you))\b", "Direct physical violence threat"),
            (r"\b(?:he|she|they|you)\s+(?:will\s+be\s+harmed|will\s+be\s+hurt|will\s+be\s+killed|will\s+die|gets?\s+hurt|gets?\s+killed|dies?)\b", "Threat of death or physical harm to hostage/victim"),
            (r"\b(?:in\s+(?:my|our)\s+hands?|in\s+my\s+hand|in\s+my\s+custody|held\s+hostage|kidnapped|abducted|captive)\b", "Hostage, kidnapping, or physical captivity claim"),
            (r"\b(?:releasing\s+(?:him|her|them)|release\s+(?:him|her|them|your\s+\w+)|let\s+(?:him|her|them)\s+go|see\s+(?:him|her|them)\s+again|never\s+see\s+(?:him|her|them)\s+again)\b", "Ransom release condition or disappearance threat"),
            (r"\b(?:regret\s+it\s+if\s+you\s+don'?t|you'll\s+regret\s+it|suffer\s+the\s+consequences)\b", "Coercive conditional ultimatum"),
            (r"\b(?:if\s+you\s+(?:care|want\s+to\s+see)\s+(?:about\s+)?(?:him|her|them))\b", "Emotional coercion or hostage ultimatum"),
            # Legal / arrest / law enforcement pressure
            (r"\b(?:got\s+arrested|arrested|face\s+arrest|arrest\s+warrant|police\s+will\s+arrive|lawsuit|legal\s+action|in\s+jail|in\s+custody|bail\s+money)\b", "Threat of immediate arrest, detention, or emergency coercion"),
            (r"\b(?:penalty|fine|disciplinary\s+action|terminated|fired|suspended\s+permanently)\b", "Threat of employment or financial penalty"),
            (r"\b(?:your\s+account\s+has\s+been\s+compromised|illegal\s+activities\s+detected)\b", "Coercive claim of illegal activity detection"),
        ],
        "TOO_GOOD_TO_BE_TRUE": [
            (r"\b(?:guaranteed\s+(?:\w+\s+){0,4}(?:returns?|profit|income|payouts?)|100x|double\s+your\s+money|lottery|lucky\s+draw|sweepstakes|won\s+(?:\d+|ten|twenty|fifty|a\s+million|a\s+crore|lakh|thousand))\b", "Unrealistic guaranteed return / prize promise"),
            (r"\b(?:exclusive\s+investment|claim\s+your\s+prize|free\s+crypto|risk[- ]free\s+opportunity|trading\s+bot)\b", "Fraudulent investment/prize claim"),
        ],
        "REMOTE_ACCESS_LINKS": [
            (r"\b(?:anydesk|teamviewer|quicksupport|ultraviewer|zoho\s+assist|remote\s+desktop)\b", "Remote control software installation request"),
            (r"\b(?:install\s+(?:this\s+)?(?:app|software|tool|file)|download\s+the\s+attached)\b", "Instruction to download or install external software"),
            (r"\b(?:click\s+(?:the\s+)?(?:link|button)|go\s+to\s+this\s+(?:website|url)|share\s+your\s+screen)\b", "Instruction to click unverified link or share screen"),
        ],
    }

    # Action directive patterns (action_name, pattern)
    ACTION_PATTERNS = [
        ("SEND_MONEY", r"\b(?:please\s+)?(?:send|pay|deposit|remit|give|transfer|share)\s+(?:me\s+|us\s+)?(?:the\s+|this\s+|my\s+|our\s+|to\s+(?:the|this|my|our)\s+)?\s*(?:money|funds|cash|crypto|bitcoin|amount|cards?|[₹\$€£]|\d+)\b"),
        ("SEND_MONEY", r"\b(?:give\s+me|send\s+me|pay\s+me|transfer\s+me)\s+(?:[₹\$€£]|\d+[\d,]*\s*(?:crores?|lakhs?|millions?|thousands?|rupees|dollars|inr|usd|cash|funds|money))\b"),
        ("SEND_MONEY", r"\b(?:give\s+me|send\s+me|pay\s+me)\s+(?:the\s+)?(?:ransom|money|funds|cash)\b"),
        ("SEND_MONEY", r"\b(?:i\s+need\s+you\s+to|you\s+(?:must|need\s+to|have\s+to))\s+(?:send|pay|deposit|give|transfer)\s+(?:me\s+|us\s+)?(?:the\s+|this\s+|my\s+|our\s+)?\s*(?:funds|money)\b"),
        ("SEND_MONEY", r"\b(?:can\s+you|could\s+you)\s+(?:send|pay|deposit|give|transfer)\s+(?:me\s+|us\s+)?(?:the\s+|this\s+|my\s+|our\s+)?\s*(?:money|funds|cash|[\$₹€£]|\d+)\b"),
        ("SEND_MONEY", r"\b(?:send|pay|deposit|give|transfer)\s+(?:me\s+)?(?:[₹\$€£]|\d+[\d,]*\s*(?:rupees|dollars|inr|usd|cash|funds|money))\b"),
        ("SEND_MONEY", r"\b(?:need\s+(?:.*?\b)?(?:bail\s+money|ransom|funds|money)\s+sent)\b"),
        ("SEND_MONEY", r"\b(?:pay\s+(?:the\s+)?(?:\w+\s+){0,3}(?:processing\s+tax|processing\s+fee|tax|fee|bail)\s+immediately)\b"),
        ("SEND_MONEY", r"\b(?:arrange\s+(?:the\s+)?(?:money|funds|cash))\b"),
        ("INVEST_MONEY", r"\b(?:invest\s+(?:.*?\b)?(?:rupees|dollars|inr|usd|crypto|money|ten\s+thousand|thousand))\b"),
        ("TRANSFER_MONEY", r"\b(?:please\s+)?(?:transfer|wire)\s+(?:me\s+|us\s+)?(?:the\s+|this\s+|my\s+|our\s+)?\s*(?:funds?|money|balance|amount|sum|[₹\$€£]|\d+)\b"),
        ("TRANSFER_MONEY", r"\b(?:i\s+need\s+you\s+to|you\s+(?:must|need\s+to|have\s+to))\s+(?:transfer|wire)\s+(?:the\s+)?(?:funds?|money|sum|amount|[₹\$€£]|\d+)\b"),
        ("TRANSFER_MONEY", r"\b(?:transfer|wire)\s+(?:funds?|money)\s+immediately\b"),
        ("TRANSFER_MONEY", r"\b(?:transfer|wire)\s+(?:to\s+(?:the|this)\s+new\s+account)\b"),
        ("TRANSFER_MONEY", r"\b(?:card\s+isn'?t\s+working|account\s+is\s+locked|need\s+a\s+favor).*?(?:make\s+a\s+(?:small\s+)?transfer|transfer\s+(?:me\s+)?some|send\s+(?:me\s+)?some)\b"),
        ("TRANSFER_MONEY", r"\b(?:make\s+a\s+(?:small\s+)?transfer)\b"),
        ("SHARE_OTP", r"\b(?:give|send|tell|share|read\s+out|provide)\s+(?:.*?\b)?(?:otp\s+verification\s+code|otp\s+code|otp|one[- ]time\s+pass(?:code|word)?|verification\s+code|2fa\s+code)\b"),
        ("SHARE_PASSWORD", r"\b(?:give|send|tell|share|provide)\s+(?:.*?\b)?(?:password|pin|credentials|login)\b"),
        ("SHARE_BANK_DETAILS", r"\b(?:share|give|send|provide)\s+(?:.*?\b)?(?:bank\s+details|account\s+details|card\s+number|cvv)\b"),
        ("CLICK_LINK", r"\b(?:click\s+(?:on\s+)?(?:this|the)\s+link|open\s+(?:this|the)\s+link|follow\s+this\s+link)\b"),
        ("INSTALL_REMOTE_ACCESS", r"\b(?:install|download|run)\s+(?:anydesk|teamviewer|quicksupport|remote\s+access|the\s+app|the\s+file)\b"),
        ("SHARE_SCREEN", r"\b(?:share\s+your\s+screen|grant\s+access|give\s+control)\b"),
        ("CHANGE_PAYMENT_ACCOUNT", r"\b(?:update|change)\s+(?:the\s+)?(?:bank|invoice|payment|beneficiary|account)\s+(?:details|number|destination)\b"),
        ("KEEP_SECRET", r"\b(?:don'?t|do\s+not|never)\s+(?:\w+\s+){0,3}(?:tell|inform|contact|call|notify)\s+(?:the\s+police|police|anyone|authorities|cops)\b"),
        ("KEEP_SECRET", r"\b(?:don'?t\s+(?:\w+\s+){0,2}tell|keep\s+this\s+(?:secret|confidential|between\s+us|quiet))\b"),
        ("CONTACT_NEW_NUMBER", r"\b(?:message|text|contact|call)\s+(?:me\s+)?(?:on|at)\s+(?:this\s+new\s+number|whatsapp|telegram|my\s+cell)\b"),
    ]

    # Patterns indicating educational / news / awareness context
    NEWS_AWARENESS_PATTERNS = [
        r"\b(?:beware\s+of|be\s+careful\s+of|watch\s+out\s+for|scammers?\s+(?:are|often|use|try|will|trick|ask|target))\b",
        r"\b(?:in\s+this\s+(?:report|video|news|segment|story|documentary)|news\s+anchor|reporting\s+live)\b",
        r"\b(?:cybersecurity\s+tip|safety\s+warning|fraud\s+awareness|psa|public\s+service\s+announcement)\b",
        r"\b(?:police\s+warn(?:ed)?|officials\s+caution|fbi\s+warns|victims\s+were\s+targeted|how\s+scams?\s+work|scam\s+alert)\b",
        r"\b(?:video\s+is\s+about\s+how\s+scammers|discussing\s+how\s+scammers|educational\s+purposes\s+only|demonstration\s+of\s+a\s+scam)\b",
        r"\b(?:awareness\s+campaign|warning\s+(?:the\s+public|viewers|citizens)|fraud\s+investigation\s+report)\b",
        r"\b(?:police\s+warn(?:ed)?\s+(?:people|citizens)?\s*not\s+to\s+(?:send|wire|transfer)\s+money)\b",
        r"\b(?:warn(?:ed)?\s+(?:people|citizens)?\s*not\s+to\s+(?:send|share|transfer))\b",
    ]
    # Contextual filters: Jokes, legitimate peer repayments, and negations
    JOKE_PATTERNS = [
        r"(?:😂|🤣|😹|lol|lmao|rofl|just\s+kidding|jk\b|only\s+joking|haha|hahaha|bro\s*😂)",
    ]

    LEGITIMATE_CONTEXT_PATTERNS = [
        r"\b(?:you\s+owe\s+me|owe\s+me|split\s+the\s+bill|reimburse|dinner\s+share|lunch\s+money)\b",
        r"\b(?:return\s+my\s+money|pay\s+me\s+back|give\s+me\s+back\s+my\s+money)\b",
        r"\b(?:report\s+(?:this\s+)?to\s+the\s+police|go\s+to\s+the\s+police|call\s+the\s+police\s+on\s+you)\b",
    ]

    NEGATION_PATTERN = (
        r"\b(?:never|don'?t|do\s+not|should\s+not|shouldn'?t|must\s+not|mustn'?t|"
        r"warn(?:ed|s)?\s+(?:against|not\s+to|people\s+not\s+to)|caution(?:ed|s)?\s+not\s+to)\b"
    )

    def analyze(self, speech_result: Optional[SpeechResult]) -> FraudResult:
        """Analyze transcript segments to detect fraud intent and social engineering tactics."""
        return self.evaluate(speech_result)

    def _has_direct_coercion_or_threat(self, full_transcript: str) -> bool:
        """
        Detects unambiguous direct extortion, hostage claims, or death/harm threats.
        These MUST NEVER be downgraded as news or educational reports.
        """
        direct_patterns = [
            r"\b(?:i\s+will|i'll|we\s+will|we'll|going\s+to)\s+(?:kill|hurt|harm|shoot|murder|injure)\b",
            r"\b(?:will\s+kill\s+(?:him|her|them|you)|will\s+hurt\s+(?:him|her|them|you)|will\s+shoot\s+(?:him|her|them|you))\b",
            r"\b(?:in\s+(?:my|our)\s+hands?|in\s+my\s+hand|releasing\s+(?:him|her|them)|never\s+see\s+(?:him|her|them)\s+again)\b",
            r"\b(?:give\s+me|send\s+me|pay\s+me)\s+(?:[₹\$€£]|\d+[\d,]*\s*(?:crores?|lakhs?|millions?|thousands?|rupees|dollars|inr|usd|cash|funds|money))\b",
            r"\b(?:don'?t|do\s+not)\s+(?:\w+\s+){0,3}(?:tell|inform|call)\s+(?:the\s+police|police|anyone)\b",
            r"\b(?:or\s+(?:else\s+)?(?:he|she|they|you)\s+(?:dies?|gets?\s+hurt|will\s+be\s+killed))\b",
        ]
        return any(re.search(pat, full_transcript, re.IGNORECASE) for pat in direct_patterns)

    def _is_negated_in_clause(self, text_prefix: str) -> bool:
        """
        Determines if a matched phrase is negated within its immediate clause.
        Punctuation (comma, period) and coordinating conjunctions (or, otherwise, else)
        terminate the scope of preceding negations.
        """
        if not text_prefix or not text_prefix.strip():
            return False
        clauses = re.split(r"[,;:.!?]|\b(?:or|otherwise|else|then)\b", text_prefix)
        last_clause = clauses[-1].strip() if clauses else ""
        if not last_clause:
            return False
        return bool(re.search(self.NEGATION_PATTERN, last_clause, re.IGNORECASE))

    def evaluate(self, speech_result: Optional[SpeechResult]) -> FraudResult:
        """Evaluate transcript segments to detect fraud intent and social engineering tactics."""
        if not speech_result or not speech_result.available or not speech_result.segments:
            logger.info("FraudIntentEngine: No speech transcript segments available to analyze.")
            return FraudResult(
                level="NOT_ASSESSABLE",
                categories=[],
                requested_actions=[],
                news_context_downgrade=False,
            )

        segments = speech_result.segments
        full_transcript = " ".join(seg.text for seg in segments).lower()

        # 1. Detect direct coercion, jokes, settlements, and news context
        has_direct_threat = self._has_direct_coercion_or_threat(full_transcript)
        is_joke = any(re.search(pat, full_transcript, re.IGNORECASE) for pat in self.JOKE_PATTERNS)
        is_legitimate_settlement = (
            any(re.search(pat, full_transcript, re.IGNORECASE) for pat in self.LEGITIMATE_CONTEXT_PATTERNS)
            if not has_direct_threat else False
        )
        is_news_context = self._detect_news_context(full_transcript) if not has_direct_threat else False

        # 2. Match Categories across segments with reason annotations (respecting negations)
        categories_found: List[FraudCategoryEvidence] = []
        for cat_name, pattern_tuples in self.CATEGORY_PATTERNS.items():
            evidence_items: List[FraudEvidenceItem] = []
            for seg in segments:
                text_clean = seg.text.strip()
                for pat, reason_desc in pattern_tuples:
                    matches = list(re.finditer(pat, text_clean, re.IGNORECASE))
                    for m in matches:
                        # Check clause-scoped negation prefix
                        prefix = text_clean[:m.start()].strip()
                        if self._is_negated_in_clause(prefix):
                            continue
                        evidence_items.append(
                            FraudEvidenceItem(
                                phrase=m.group(0),
                                start_s=seg.start_s,
                                end_s=seg.end_s,
                                reason=reason_desc,
                            )
                        )
            if evidence_items:
                severity = "HIGH" if cat_name in ("PAYMENT_CREDENTIAL", "THREAT_PRESSURE", "REMOTE_ACCESS_LINKS") else "MEDIUM"
                categories_found.append(
                    FraudCategoryEvidence(
                        category=cat_name,
                        severity=severity,
                        evidence=evidence_items,
                    )
                )

        # 3. Detect Directed Action Requests (filtering negated educational phrases)
        requested_actions: List[FraudRequestedAction] = []
        for seg in segments:
            text_clean = seg.text.strip()
            for action_name, pat in self.ACTION_PATTERNS:
                matches = list(re.finditer(pat, text_clean, re.IGNORECASE))
                for m in matches:
                    prefix = text_clean[:m.start()].strip()
                    if self._is_negated_in_clause(prefix):
                        continue
                    # Prevent duplicate actions on same segment
                    if not any(a.action == action_name and a.start_s == seg.start_s for a in requested_actions):
                        requested_actions.append(
                            FraudRequestedAction(
                                action=action_name,
                                phrase=m.group(0),
                                start_s=seg.start_s,
                                end_s=seg.end_s,
                            )
                        )

        # 4. Multi-signal scoring & determination of raw risk level
        raw_level = self._compute_fraud_level(categories_found, requested_actions, full_transcript)

        # 5. Apply context downgrades: Jokes, Legitimate debt settlement, News/Awareness
        final_level = raw_level
        downgraded = False
        if is_joke:
            final_level = "LOW"
            downgraded = True
            logger.info("FraudIntentEngine: Downgraded fraud risk to LOW due to joke/banter context.")
        elif is_legitimate_settlement:
            final_level = "LOW"
            downgraded = True
            logger.info("FraudIntentEngine: Downgraded fraud risk to LOW due to peer debt settlement context.")
        elif is_news_context and not has_direct_threat and raw_level in ("HIGH", "MEDIUM"):
            downgraded = True
            if raw_level == "HIGH":
                final_level = "MEDIUM"
            elif raw_level == "MEDIUM":
                final_level = "LOW"
            logger.info(f"FraudIntentEngine: Downgraded fraud risk {raw_level} -> {final_level} due to news/educational context.")

        logger.info(
            f"FraudIntentEngine Analysis: level={final_level} (raw={raw_level}, downgraded={downgraded}) | "
            f"categories={[c.category for c in categories_found]} | actions={[a.action for a in requested_actions]}"
        )

        return FraudResult(
            level=final_level,
            categories=categories_found,
            requested_actions=requested_actions,
            news_context_downgrade=downgraded,
        )

    def _detect_news_context(self, full_transcript: str) -> bool:
        if self._has_direct_coercion_or_threat(full_transcript):
            return False
        for pat in self.NEWS_AWARENESS_PATTERNS:
            if re.search(pat, full_transcript, re.IGNORECASE):
                return True
        return False

    def _compute_fraud_level(
        self,
        categories: List[FraudCategoryEvidence],
        requested_actions: List[FraudRequestedAction],
        full_transcript: str = "",
    ) -> str:
        cat_names = {c.category for c in categories}
        action_names = {a.action for a in requested_actions}

        has_direct_action = len(requested_actions) > 0
        has_payment_creds = "PAYMENT_CREDENTIAL" in cat_names
        has_authority = "AUTHORITY" in cat_names
        has_urgency = "URGENCY" in cat_names
        has_threat = "THREAT_PRESSURE" in cat_names
        has_secrecy = "SECRECY" in cat_names
        has_remote = "REMOTE_ACCESS_LINKS" in cat_names
        has_channel_change = "CHANNEL_IDENTITY_CHANGE" in cat_names
        has_too_good = "TOO_GOOD_TO_BE_TRUE" in cat_names

        # Critical Direct Violent / Ransom / Hostage Threat -> immediate HIGH
        if self._has_direct_coercion_or_threat(full_transcript):
            return "HIGH"

        # Direct money extraction combined with social engineering coercion -> HIGH
        if action_names & {"SEND_MONEY", "TRANSFER_MONEY", "INVEST_MONEY"}:
            if has_authority or has_urgency or has_threat or has_secrecy or has_channel_change or has_too_good:
                return "HIGH"
            # Casual money request without social engineering pressure -> MEDIUM
            return "MEDIUM"

        # Strong Social Engineering combos without explicit action regex trigger -> HIGH
        if has_threat and (has_payment_creds or has_secrecy or has_urgency):
            return "HIGH"
        if has_authority and has_urgency and has_payment_creds:
            return "HIGH"
        if has_remote and has_urgency:
            return "HIGH"

        # Credential extraction requires urgency/authority/threat/pressure to be HIGH
        if action_names & {"SHARE_OTP", "SHARE_PASSWORD", "SHARE_BANK_DETAILS"}:
            if has_urgency or has_authority or has_threat or has_secrecy or len(cat_names) >= 2:
                return "HIGH"
            return "MEDIUM"

        if action_names & {"INSTALL_REMOTE_ACCESS"}:
            if has_urgency or has_authority or has_threat:
                return "HIGH"
            return "MEDIUM"

        # Medium Risk indicators
        if len(cat_names) >= 2:
            return "MEDIUM"
        if has_payment_creds or has_too_good or has_remote or has_threat:
            return "MEDIUM"
        if has_authority or has_urgency or has_secrecy or has_channel_change:
            return "MEDIUM"

        return "LOW"
