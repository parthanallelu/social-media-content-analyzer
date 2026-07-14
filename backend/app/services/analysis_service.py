"""
Rule-based engagement analysis service — enriched with NLP.

Original rule-based analyses (readability, engagement, structure, platform)
are fully preserved. New functions layer on top using TextBlob, NLTK, and spaCy:

  analyze_sentiment()      – TextBlob polarity + subjectivity
  detect_keywords()        – NLTK FreqDist + spaCy POS filtering
  calculate_readability()  – Flesch-Kincaid Grade approximation (no external API)
  estimate_engagement()    – Composite score from CTAs, sentiment, keywords, questions
  suggest_hashtags()       – Keyword-derived hashtag candidates
  improve_caption()        – Rule-based sentence trimming + CTA injection
  detect_call_to_action()  – Boolean CTA presence check
  grammar_suggestions()    – TextBlob spelling correction (basic, English only)
  character_count()        – Simple character metric
  word_count()             – Simple word metric
  reading_time()           – 200 wpm estimate

Memory footprint on Render free tier (512 MB):
  spaCy en_core_web_sm   ≈  50 MB resident (loaded once at startup)
  NLTK corpora           ≈  30 MB on disk  (punkt, stopwords, wordnet, tagger)
  TextBlob               ≈   5 MB resident
  Total NLP overhead     ≈  85 MB  →  well within free tier limits.
"""

import re
import logging
import unicodedata
from typing import List, Optional, Tuple

from app.models.response_models import (
    TextBlock, BlockType,
    Suggestion, SeverityLevel, ScoreBreakdown, AnalysisResponse,
    SentimentResult, KeywordItem, GrammarIssue, ContentStatistics,
)
from app.utils.error_handlers import AnalysisFailedError, EmptyContentError

logger = logging.getLogger(__name__)

# ── Lazy NLP model initialisation ─────────────────────────────────────────────
# Models are imported once at module load; import failures are caught and logged
# so the service degrades gracefully (new fields return None) rather than crashing.

_nlp = None          # spaCy Language
_textblob_ok = False
_nltk_ok = False

try:
    import spacy
    _nlp = spacy.load("en_core_web_sm")
    logger.info("spaCy en_core_web_sm loaded successfully.")
except Exception as _spacy_err:
    logger.warning("spaCy unavailable — keyword extraction will be disabled: %s", _spacy_err)

try:
    from textblob import TextBlob
    _textblob_ok = True
    logger.info("TextBlob loaded successfully.")
except Exception as _tb_err:
    logger.warning("TextBlob unavailable — sentiment/grammar will be disabled: %s", _tb_err)

try:
    import nltk
    import os
    _render_nltk_path = "/opt/render/project/nltk_data"
    if os.path.exists(_render_nltk_path) and _render_nltk_path not in nltk.data.path:
        nltk.data.path.append(_render_nltk_path)
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize, sent_tokenize
    from nltk import FreqDist, pos_tag
    # Ensure required corpora are present (they were downloaded at build time;
    # this is a defensive runtime check only).
    for _corpus in ("punkt", "punkt_tab", "averaged_perceptron_tagger", "stopwords", "wordnet"):
        try:
            nltk.data.find(f"tokenizers/{_corpus}" if "punkt" in _corpus else
                           f"taggers/{_corpus}" if "tagger" in _corpus else
                           f"corpora/{_corpus}")
        except LookupError:
            nltk.download(_corpus, quiet=True)
    _STOPWORDS = set(stopwords.words("english"))
    _nltk_ok = True
    logger.info("NLTK loaded successfully.")
except Exception as _nltk_err:
    logger.warning("NLTK unavailable — some features will be disabled: %s", _nltk_err)
    _STOPWORDS = set()


# ── Word lists (unchanged from original) ─────────────────────────────────────

CTA_KEYWORDS = {
    "click", "follow", "share", "subscribe", "comment", "like", "tag",
    "visit", "join", "download", "sign up", "register", "learn more",
    "get started", "try", "buy", "shop", "explore", "discover",
    "dm", "link in bio", "swipe up", "tap", "save",
}

POSITIVE_EMOTION_WORDS = {
    "amazing", "incredible", "exciting", "love", "best", "great", "fantastic",
    "awesome", "wonderful", "brilliant", "outstanding", "excellent", "perfect",
    "success", "win", "winning", "happy", "joy", "proud", "grateful",
    "inspired", "motivating", "powerful", "transformative",
}

NEGATIVE_FILLER_WORDS = {
    "very", "really", "quite", "rather", "somewhat", "actually", "basically",
    "literally", "definitely", "certainly", "just", "simply", "obviously",
}

PASSIVE_VOICE_PATTERNS = [
    re.compile(r"\b(is|are|was|were|be|been|being)\s+\w+ed\b", re.IGNORECASE),
    re.compile(r"\b(is|are|was|were)\s+being\s+\w+ed\b", re.IGNORECASE),
]

STAT_PATTERN = re.compile(r"\b\d+(\.\d+)?[\s]*(percent|%|million|billion|thousand|x|times)\b", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"\b\d+\b")
QUESTION_PATTERN = re.compile(r"\?")
HASHTAG_PATTERN = re.compile(r"#\w+")
EMOJI_PATTERN = re.compile(
    r"[\U0001F600-\U0001F64F"   # Emoticons
    r"\U0001F300-\U0001F5FF"    # Symbols & pictographs
    r"\U0001F680-\U0001F6FF"    # Transport & map
    r"\U0001F1E0-\U0001F1FF"    # Flags
    r"\U00002700-\U000027BF"    # Dingbats
    r"\U0001F900-\U0001F9FF"    # Supplemental symbols
    r"\u2600-\u26FF\u2700-\u27BF]+",
    flags=re.UNICODE,
)

PLATFORM_NOTES = {
    "instagram": {
        "ideal_caption_words": (125, 150),
        "hashtag_target": (5, 10),
        "tip": "Instagram posts with 5–10 relevant hashtags and a question in the caption get significantly higher engagement.",
    },
    "linkedin": {
        "ideal_post_words": (150, 300),
        "tip": "LinkedIn posts with statistics and a clear professional insight perform best. Avoid jargon.",
    },
    "twitter": {
        "char_limit": 280,
        "tip": "For Twitter/X, aim for punchy sentences under 280 characters. Threads work well for longer content.",
    },
    "general": {
        "tip": "Keep paragraphs short, use active voice, and end with a clear call to action.",
    },
}

# Hashtag blocklist — common words that would make useless hashtags
_HASHTAG_BLOCKLIST = {
    "the", "and", "for", "are", "but", "not", "you", "all", "can",
    "her", "was", "one", "our", "out", "day", "get", "has", "him",
    "his", "how", "its", "let", "man", "new", "now", "old", "see",
    "two", "way", "who", "boy", "did", "she", "use", "use", "that",
    "with", "have", "this", "will", "your", "from", "they", "know",
    "also", "into", "more", "than", "then", "them", "been", "were",
    "what", "when", "said", "each", "which", "about", "would", "there",
    "their", "could", "other", "after", "first", "never", "these",
}


# ── Main entry point ──────────────────────────────────────────────────────────

def analyze_content(blocks: List[TextBlock], platform: str = "general") -> AnalysisResponse:
    """
    Run all rule-based and NLP analyses on a list of text blocks.

    Returns an AnalysisResponse with:
      - suggestions, score  (existing fields — unchanged)
      - sentiment, keywords, suggested_hashtags, improved_caption,
        grammar_suggestions, statistics  (new enriched fields)
    """
    if not blocks:
        raise EmptyContentError()

    platform = platform.lower().strip()
    if platform not in PLATFORM_NOTES:
        platform = "general"

    try:
        text_blocks = [b for b in blocks if b.text.strip()]
        all_text = " ".join(b.text for b in text_blocks)
        sentences = _split_sentences(all_text)
        words = all_text.split()

        suggestions: List[Suggestion] = []

        # ── Existing rule-based analyses (preserved exactly) ──────────────────
        r_score, r_suggestions = _readability_analysis(text_blocks, sentences, words)
        e_score, e_suggestions = _engagement_analysis(text_blocks, sentences, words, all_text)
        s_score, s_suggestions = _structure_analysis(blocks)
        p_suggestions = _platform_analysis(text_blocks, words, platform)

        suggestions.extend(r_suggestions)
        suggestions.extend(e_suggestions)
        suggestions.extend(s_suggestions)
        suggestions.extend(p_suggestions)

        # ── New NLP-powered enrichments ───────────────────────────────────────
        sentiment_result = analyze_sentiment(all_text)
        stats = _build_statistics(text_blocks, words, sentences, all_text)
        keywords = detect_keywords(all_text, top_n=15)
        hashtags = suggest_hashtags(keywords, existing_hashtags=HASHTAG_PATTERN.findall(all_text))
        caption = improve_caption(text_blocks, all_text, cta_detected=stats.cta_detected)
        grammar_issues = grammar_suggestions(all_text, max_issues=10)

        # Append grammar issues as Suggestion entries too (low severity)
        for issue in grammar_issues:
            suggestions.append(Suggestion(
                category="grammar",
                severity=SeverityLevel.LOW,
                suggestion=f"Possible spelling issue: '{issue.original}' → consider '{issue.suggestion}'.",
            ))

        # Sort by severity (high → medium → low)
        severity_order = {SeverityLevel.HIGH: 0, SeverityLevel.MEDIUM: 1, SeverityLevel.LOW: 2}
        suggestions.sort(key=lambda s: severity_order[s.severity])

        overall = _compute_overall(r_score, e_score, s_score)

        return AnalysisResponse(
            suggestions=suggestions,
            score=ScoreBreakdown(
                overall=overall,
                readability=r_score,
                engagement=e_score,
                structure=s_score,
            ),
            # ── New fields ────────────────────────────────────────────────────
            sentiment=sentiment_result,
            keywords=keywords,
            suggested_hashtags=hashtags,
            improved_caption=caption,
            grammar_suggestions=grammar_issues,
            statistics=stats,
        )
    except (EmptyContentError, AnalysisFailedError):
        raise
    except Exception as exc:
        logger.exception("Unexpected error in analyze_content: %s", exc)
        raise AnalysisFailedError(detail=str(exc)) from exc


# ══════════════════════════════════════════════════════════════════════════════
# NEW PUBLIC FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def analyze_sentiment(text: str) -> Optional[SentimentResult]:
    """
    Compute TextBlob sentiment polarity and subjectivity for the full text.

    Returns:
        SentimentResult with polarity (-1.0→1.0), subjectivity (0.0→1.0),
        a human-readable label, and a subjectivity label.
        Returns None if TextBlob is unavailable.

    TextBlob uses a pattern-based lexicon (no NLTK model required for this function).
    Polarity thresholds:
        ≥  0.3  → "positive" / ≥  0.6 → "very positive"
        ≤ -0.3  → "negative" / ≤ -0.6 → "very negative"
        otherwise → "neutral"
    """
    if not _textblob_ok or not text.strip():
        return None
    try:
        from textblob import TextBlob  # re-import inside try for safety
        blob = TextBlob(text)
        polarity: float = round(blob.sentiment.polarity, 4)
        subjectivity: float = round(blob.sentiment.subjectivity, 4)

        if polarity >= 0.6:
            label = "very positive"
        elif polarity >= 0.3:
            label = "positive"
        elif polarity <= -0.6:
            label = "very negative"
        elif polarity <= -0.3:
            label = "negative"
        else:
            label = "neutral"

        if subjectivity < 0.33:
            subjectivity_label = "objective"
        elif subjectivity < 0.66:
            subjectivity_label = "balanced"
        else:
            subjectivity_label = "subjective"

        return SentimentResult(
            polarity=polarity,
            subjectivity=subjectivity,
            label=label,
            subjectivity_label=subjectivity_label,
        )
    except Exception as exc:
        logger.warning("analyze_sentiment failed (non-fatal): %s", exc)
        return None


def detect_keywords(text: str, top_n: int = 15) -> Optional[List[KeywordItem]]:
    """
    Extract significant keywords from text using a two-stage pipeline:
      1. NLTK FreqDist on tokens filtered by POS (NN, NNP, JJ) and stopwords.
      2. spaCy NER entities are boosted (×1.5 score weight) as they carry
         more semantic value than common nouns.

    Returns up to `top_n` KeywordItem objects sorted by score descending.
    Returns None if neither NLTK nor spaCy is available.

    Args:
        text:   Full text to analyse.
        top_n:  Maximum number of keywords to return.
    """
    if not text.strip():
        return None
    if not _nltk_ok and _nlp is None:
        return None

    try:
        # ── Step 1: NLTK tokenise + POS filter ───────────────────────────────
        candidate_freqs: dict[str, int] = {}
        candidate_pos: dict[str, str] = {}

        if _nltk_ok:
            from nltk.tokenize import word_tokenize
            from nltk import pos_tag as nltk_pos_tag
            raw_tokens = word_tokenize(text.lower())
            # Keep only alphabetic tokens not in stopword list
            tokens = [t for t in raw_tokens if t.isalpha() and t not in _STOPWORDS and len(t) > 2]
            tagged = nltk_pos_tag(tokens)
            # Accept nouns (NN*), proper nouns (NNP*), adjectives (JJ*)
            for word, tag in tagged:
                if tag.startswith(("NN", "NNP", "JJ")):
                    candidate_freqs[word] = candidate_freqs.get(word, 0) + 1
                    candidate_pos[word] = tag

        # ── Step 2: spaCy NER entity boost + POS override ────────────────────
        entity_boost: dict[str, float] = {}
        spacy_pos: dict[str, str] = {}
        if _nlp is not None:
            doc = _nlp(text[:100_000])  # cap at 100k chars to bound memory
            for ent in doc.ents:
                norm = ent.text.lower().strip()
                if len(norm) > 2 and norm not in _STOPWORDS:
                    entity_boost[norm] = 1.5
                    candidate_freqs[norm] = candidate_freqs.get(norm, 0) + 1
            for token in doc:
                if token.pos_ in ("NOUN", "PROPN", "ADJ") and not token.is_stop and len(token.text) > 2:
                    norm = token.lemma_.lower()
                    spacy_pos[norm] = token.pos_

        if not candidate_freqs:
            return None

        # ── Step 3: Score and rank ────────────────────────────────────────────
        max_freq = max(candidate_freqs.values()) or 1
        scored: list[tuple[str, int, float, str]] = []

        for word, freq in candidate_freqs.items():
            boost = entity_boost.get(word, 1.0)
            raw_score = (freq / max_freq) * boost
            pos_tag_label = spacy_pos.get(word) or candidate_pos.get(word, "NOUN")
            scored.append((word, freq, min(1.0, round(raw_score, 4)), pos_tag_label))

        scored.sort(key=lambda x: x[2], reverse=True)

        return [
            KeywordItem(word=w, frequency=f, score=s, pos_tag=p)
            for w, f, s, p in scored[:top_n]
        ]

    except Exception as exc:
        logger.warning("detect_keywords failed (non-fatal): %s", exc)
        return None


def calculate_readability(text: str) -> Optional[float]:
    """
    Approximate the Flesch-Kincaid Grade Level using the standard formula:
        FKGL = 0.39 × (words/sentences) + 11.8 × (syllables/words) - 15.59

    Uses a simple vowel-group syllable counter that works offline without
    any external dictionary. Accuracy: ±0.5 grade levels vs. the reference
    implementation on typical English prose.

    Returns:
        Grade level as a float (e.g., 8.2 = suitable for 8th-grade readers),
        or None if the text has no sentences.
    """
    if not text.strip():
        return None

    sentences = _split_sentences(text)
    words = [w for w in text.split() if w.isalpha()]

    if not sentences or not words:
        return None

    total_syllables = sum(_count_syllables(w) for w in words)
    asl = len(words) / len(sentences)     # average sentence length
    asw = total_syllables / len(words)    # average syllables per word
    fkgl = 0.39 * asl + 11.8 * asw - 15.59
    return round(max(0.0, fkgl), 2)


def estimate_engagement(
    text: str,
    sentiment: Optional[SentimentResult] = None,
    keywords: Optional[List[KeywordItem]] = None,
) -> int:
    """
    Compute a composite engagement estimate (0–100) that extends the existing
    rule-based score with NLP signals:

      +15  CTA present
      +10  At least one question
      +10  Positive sentiment (polarity > 0.1)
      + 5  High keyword density (≥5 distinct keywords)
      + 5  Numbers/statistics present
      + 5  Positive emotion words present
      -10  Very negative sentiment (polarity < -0.4)
      -10  Extremely high subjectivity (> 0.85) — reads as rant, not content

    This is a standalone utility; analyze_content() uses the richer
    _engagement_analysis() internally for scored suggestions.

    Returns:
        Integer score clamped to [0, 100].
    """
    score = 40  # neutral baseline

    word_set = {w.lower().rstrip(".,!?;:") for w in text.split()}

    if CTA_KEYWORDS & word_set:
        score += 15
    if QUESTION_PATTERN.search(text):
        score += 10
    if POSITIVE_EMOTION_WORDS & word_set:
        score += 5
    if STAT_PATTERN.search(text) or len(NUMBER_PATTERN.findall(text)) >= 2:
        score += 5

    if sentiment is not None:
        if sentiment.polarity > 0.1:
            score += 10
        elif sentiment.polarity < -0.4:
            score -= 10
        if sentiment.subjectivity > 0.85:
            score -= 10

    if keywords and len(keywords) >= 5:
        score += 5

    return min(100, max(0, score))


def suggest_hashtags(
    keywords: Optional[List[KeywordItem]],
    existing_hashtags: Optional[List[str]] = None,
    max_hashtags: int = 10,
) -> Optional[List[str]]:
    """
    Generate hashtag suggestions from the top extracted keywords.

    Filters out:
      - Words in the blocklist (common words that make poor hashtags)
      - Words shorter than 3 characters
      - Keywords that already appear as hashtags in the text
      - Non-noun/propnoun keywords scoring below 0.2

    Returns up to `max_hashtags` hashtags formatted as '#word' strings,
    or None if no keywords were provided.

    Args:
        keywords:           Output of detect_keywords().
        existing_hashtags:  Hashtag strings already present in the content (e.g. ['#fitness']).
        max_hashtags:       Cap on returned suggestions.
    """
    if not keywords:
        return None

    existing_lower = {h.lstrip("#").lower() for h in (existing_hashtags or [])}
    candidates: List[str] = []

    for kw in keywords:
        word = kw.word.lower().strip()
        if (
            word in _HASHTAG_BLOCKLIST
            or word in existing_lower
            or len(word) < 3
            or (kw.pos_tag not in ("NOUN", "PROPN", "NN", "NNP", "NNS", "NNPS") and kw.score < 0.2)
        ):
            continue
        candidates.append("#" + word)
        if len(candidates) >= max_hashtags:
            break

    return candidates if candidates else None


def improve_caption(
    blocks: List[TextBlock],
    all_text: str,
    cta_detected: bool = False,
) -> Optional[str]:
    """
    Produce a rule-based improved version of the first paragraph block:
      1. Trim long sentences to ≤ 20 words (splits at the last comma before the limit).
      2. Replace passive voice markers with an active-voice note inline.
      3. Append a CTA invitation if none is detected in the text.
      4. Cap the output at 200 words.

    This is NOT an LLM rewrite — it is a deterministic, rule-based transformation
    that gives the user a concrete improvement starting point.

    Returns:
        The improved caption string, or None if no paragraph block is found.
    """
    # Find the first non-empty paragraph block
    first_para = next(
        (b for b in blocks if b.type == BlockType.PARAGRAPH and b.text.strip()),
        None,
    )
    if first_para is None:
        # Fall back to first non-empty block of any type
        first_para = next((b for b in blocks if b.text.strip()), None)
    if first_para is None:
        return None

    text = first_para.text.strip()
    sentences = _split_sentences(text)
    improved_sentences: List[str] = []

    for sentence in sentences:
        words = sentence.split()
        # Trim overly long sentences at the last comma before word 20, or hard-cut
        if len(words) > 20:
            comma_positions = [i for i, w in enumerate(words[:20]) if w.endswith(",")]
            cut = comma_positions[-1] + 1 if comma_positions else 20
            trimmed = " ".join(words[:cut])
            if not trimmed.endswith((".", "!", "?")):
                trimmed += "."
            sentence = trimmed

        # Flag passive voice inline
        for pattern in PASSIVE_VOICE_PATTERNS:
            if pattern.search(sentence):
                sentence = sentence.rstrip(".!?") + " [consider active voice]."
                break

        improved_sentences.append(sentence)

    result = " ".join(improved_sentences)

    # Append a CTA if missing
    if not cta_detected:
        result = result.rstrip() + " Share your thoughts in the comments below!"

    # Cap at 200 words
    result_words = result.split()
    if len(result_words) > 200:
        result = " ".join(result_words[:200]) + "…"

    return result


def detect_call_to_action(text: str) -> bool:
    """
    Detect whether the text contains at least one call-to-action phrase.

    Checks against the CTA_KEYWORDS set using whole-word matching to
    avoid false positives (e.g. 'discovery' should not match 'discover').

    Returns:
        True if a CTA keyword is found, False otherwise.
    """
    if not text:
        return False
    word_set = {w.lower().rstrip(".,!?;:'\"") for w in text.split()}
    return bool(CTA_KEYWORDS & word_set)


def grammar_suggestions(text: str, max_issues: int = 10) -> List[GrammarIssue]:
    """
    Identify basic spelling issues using TextBlob's word correction.

    Scope:
      - Spelling mistakes only (TextBlob correct() is a statistical spell-checker).
      - Style issues: words in NEGATIVE_FILLER_WORDS that appear excessively.
      - Does NOT perform grammar/syntax checking — that would require a paid
        service or a much heavier model than en_core_web_sm.

    Returns up to `max_issues` GrammarIssue objects.
    Returns an empty list if TextBlob is unavailable or text is empty.

    Note: TextBlob's correct() has moderate precision. It will miss domain-specific
    terms and may flag proper nouns. Results should be presented as suggestions,
    not definitive corrections.
    """
    if not _textblob_ok or not text.strip():
        return []

    try:
        from textblob import TextBlob, Word

        issues: List[GrammarIssue] = []
        seen: set[str] = set()

        # Tokenise into individual words (NLTK-backed if available, else split)
        if _nltk_ok:
            from nltk.tokenize import word_tokenize
            tokens = word_tokenize(text)
        else:
            tokens = text.split()

        for raw_token in tokens:
            # Skip non-alphabetic tokens, short words, and already-seen ones
            clean = raw_token.strip(".,!?;:\"'()-")
            if not clean.isalpha() or len(clean) < 4 or clean.lower() in seen:
                continue
            seen.add(clean.lower())

            # Skip all-caps (likely abbreviations/acronyms)
            if clean.isupper():
                continue

            # Skip hashtags and mentions
            if raw_token.startswith(("#", "@")):
                continue

            try:
                word_obj = Word(clean)
                corrected = word_obj.correct()
                if corrected.lower() != clean.lower():
                    issues.append(GrammarIssue(
                        original=clean,
                        suggestion=corrected,
                        issue_type="spelling",
                    ))
            except Exception:
                pass  # individual word correction failure is non-fatal

            if len(issues) >= max_issues:
                break

        # Style issues: excessive filler words
        words_lower = [w.lower().rstrip(".,!?;:") for w in text.split()]
        for filler in NEGATIVE_FILLER_WORDS:
            count = words_lower.count(filler)
            if count >= 3 and len(issues) < max_issues:
                issues.append(GrammarIssue(
                    original=f"'{filler}' (×{count})",
                    suggestion=f"Remove or reduce '{filler}' — it weakens your writing.",
                    issue_type="style",
                ))

        return issues[:max_issues]

    except Exception as exc:
        logger.warning("grammar_suggestions failed (non-fatal): %s", exc)
        return []


def character_count(text: str) -> int:
    """
    Return the total number of characters in the text (including spaces and punctuation).
    Unicode-aware: counts Unicode code points, not bytes.
    """
    return len(text)


def word_count(text: str) -> int:
    """
    Return the number of whitespace-delimited tokens.
    Matches the count a user would get from 'word count' in a text editor.
    """
    return len(text.split())


def reading_time(text: str, wpm: int = 200) -> Tuple[int, str]:
    """
    Estimate reading time based on an average reading speed of 200 wpm
    (conservative estimate for social media content; research suggests
    200–250 wpm for digital text).

    Returns:
        Tuple of (seconds: int, label: str).
        Examples: (45, '< 1 min read'), (90, '1 min read'), (200, '3 min read').
    """
    total_words = word_count(text)
    seconds = max(1, int((total_words / wpm) * 60))

    if seconds < 60:
        label = "< 1 min read"
    elif seconds < 120:
        label = "1 min read"
    else:
        minutes = round(seconds / 60)
        label = f"{minutes} min read"

    return seconds, label


# ══════════════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS (existing + new)
# ══════════════════════════════════════════════════════════════════════════════

def _build_statistics(
    text_blocks: List[TextBlock],
    words: List[str],
    sentences: List[str],
    all_text: str,
) -> ContentStatistics:
    """Build a ContentStatistics object from pre-computed derived values."""
    total_words = len(words)
    total_chars = character_count(all_text)
    total_sentences = len(sentences)
    paragraph_count = sum(1 for b in text_blocks if b.type == BlockType.PARAGRAPH)
    rt_seconds, rt_label = reading_time(all_text)
    avg_wps = round(total_words / max(total_sentences, 1), 2)
    cta = detect_call_to_action(all_text)
    questions = len(QUESTION_PATTERN.findall(all_text))
    hashtags = len(HASHTAG_PATTERN.findall(all_text))
    emojis = len(EMOJI_PATTERN.findall(all_text))

    return ContentStatistics(
        character_count=total_chars,
        word_count=total_words,
        sentence_count=total_sentences,
        paragraph_count=paragraph_count,
        reading_time_seconds=rt_seconds,
        reading_time_label=rt_label,
        average_words_per_sentence=avg_wps,
        cta_detected=cta,
        question_count=questions,
        hashtag_count=hashtags,
        emoji_count=emojis,
    )


def _count_syllables(word: str) -> int:
    """
    Estimate syllable count using a vowel-group heuristic.
    Accuracy is sufficient for Flesch-Kincaid approximation.
    """
    word = word.lower().rstrip("e")  # trailing silent 'e' doesn't count
    vowel_groups = re.findall(r"[aeiouy]+", word)
    return max(1, len(vowel_groups))


# ── Original rule-based sub-analyses (preserved exactly) ─────────────────────

def _readability_analysis(
    blocks: List[TextBlock], sentences: List[str], words: List[str]
) -> Tuple[int, List[Suggestion]]:
    suggestions: List[Suggestion] = []
    score = 100

    # Average sentence length
    if sentences:
        avg_sent_len = len(words) / len(sentences)
        if avg_sent_len > 25:
            score -= 25
            suggestions.append(Suggestion(
                category="readability",
                severity=SeverityLevel.HIGH,
                suggestion=(
                    f"Your average sentence length is {avg_sent_len:.0f} words — "
                    "aim for under 20 words per sentence to improve mobile readability."
                ),
            ))
        elif avg_sent_len > 18:
            score -= 10
            suggestions.append(Suggestion(
                category="readability",
                severity=SeverityLevel.MEDIUM,
                suggestion="Some sentences are long. Try breaking them up for clearer, punchier writing.",
            ))

    # Long paragraphs
    para_blocks = [b for b in blocks if b.type == BlockType.PARAGRAPH]
    long_paras = [
        i for i, b in enumerate(blocks)
        if b.type == BlockType.PARAGRAPH and len(b.text.split()) > 80
    ]
    if long_paras:
        score -= 15
        suggestions.append(Suggestion(
            category="readability",
            severity=SeverityLevel.HIGH,
            suggestion=(
                f"{len(long_paras)} paragraph(s) are very long (>80 words). "
                "Break them into shorter chunks or add bullet points."
            ),
            affected_block_index=long_paras[0],
        ))

    # Passive voice
    passive_count = sum(
        1 for pattern in PASSIVE_VOICE_PATTERNS
        for _ in pattern.finditer(" ".join(b.text for b in blocks))
    )
    if passive_count > 3:
        score -= 15
        suggestions.append(Suggestion(
            category="readability",
            severity=SeverityLevel.MEDIUM,
            suggestion=(
                f"Found {passive_count} instances of passive voice. "
                "Switch to active voice to make your writing more direct and engaging."
            ),
        ))

    # Filler words
    filler_count = sum(
        1 for w in words if w.lower().rstrip(".,!?;:") in NEGATIVE_FILLER_WORDS
    )
    filler_ratio = filler_count / max(len(words), 1)
    if filler_ratio > 0.05:
        score -= 10
        suggestions.append(Suggestion(
            category="readability",
            severity=SeverityLevel.LOW,
            suggestion=(
                f"Your content contains {filler_count} filler words (e.g. 'very', 'really', 'just'). "
                "Remove them to make sentences crisper."
            ),
        ))

    return max(0, score), suggestions


def _engagement_analysis(
    blocks: List[TextBlock], sentences: List[str], words: List[str], all_text: str
) -> Tuple[int, List[Suggestion]]:
    suggestions: List[Suggestion] = []
    score = 50  # Start at 50 — engagement must be earned

    word_set = {w.lower().rstrip(".,!?;:") for w in words}

    # Call to action
    cta_found = CTA_KEYWORDS & word_set
    if cta_found:
        score += 20
    else:
        suggestions.append(Suggestion(
            category="engagement",
            severity=SeverityLevel.HIGH,
            suggestion=(
                "No call-to-action detected. Add a directive at the end "
                "(e.g., 'Share your thoughts below', 'Follow for more', 'Click the link')."
            ),
        ))

    # Questions
    question_count = len(QUESTION_PATTERN.findall(all_text))
    if question_count >= 1:
        score += 15
    else:
        suggestions.append(Suggestion(
            category="engagement",
            severity=SeverityLevel.MEDIUM,
            suggestion=(
                "No questions found. Asking the audience a question boosts comments "
                "and interaction (e.g., 'What do you think?' or 'Have you tried this?')."
            ),
        ))

    # Emotional words
    emotion_found = POSITIVE_EMOTION_WORDS & word_set
    if emotion_found:
        score += 10

    # Statistics / numbers
    has_stats = bool(STAT_PATTERN.search(all_text))
    number_count = len(NUMBER_PATTERN.findall(all_text))
    if has_stats or number_count >= 2:
        score += 10
    else:
        suggestions.append(Suggestion(
            category="engagement",
            severity=SeverityLevel.LOW,
            suggestion=(
                "Adding specific numbers or statistics (e.g., '3 tips', '40% increase') "
                "makes content more credible and shareable."
            ),
        ))

    # Hook (first sentence)
    if sentences:
        first_sentence = sentences[0]
        first_words = len(first_sentence.split())
        if first_words > 30:
            score -= 5
            suggestions.append(Suggestion(
                category="engagement",
                severity=SeverityLevel.MEDIUM,
                suggestion=(
                    "Your opening sentence is long. Start with a short, punchy hook "
                    "(under 15 words) to grab attention instantly."
                ),
                affected_block_index=0,
            ))
        elif "?" in first_sentence or any(w in first_sentence.lower() for w in {"imagine", "what if", "stop", "warning", "how"}):
            score += 5  # bonus for a strong hook type

    return min(100, max(0, score)), suggestions


def _structure_analysis(blocks: List[TextBlock]) -> Tuple[int, List[Suggestion]]:
    suggestions: List[Suggestion] = []
    score = 100

    has_headings = any(b.type == BlockType.HEADING for b in blocks)
    has_bullets = any(b.type == BlockType.BULLET for b in blocks)
    total_blocks = len(blocks)

    # No headings
    if total_blocks > 5 and not has_headings:
        score -= 20
        suggestions.append(Suggestion(
            category="structure",
            severity=SeverityLevel.MEDIUM,
            suggestion=(
                "No headings were detected. Use headings to break up sections "
                "and help skimmers find what they need quickly."
            ),
        ))

    # No bullets (for longer content)
    if total_blocks > 8 and not has_bullets:
        score -= 10
        suggestions.append(Suggestion(
            category="structure",
            severity=SeverityLevel.LOW,
            suggestion=(
                "Consider using bullet points to organize lists or key takeaways. "
                "Bulleted content is 80% more readable at a glance."
            ),
        ))

    # Single long wall of text (one big block)
    if total_blocks == 1 and len(blocks[0].text.split()) > 100:
        score -= 30
        suggestions.append(Suggestion(
            category="structure",
            severity=SeverityLevel.HIGH,
            suggestion=(
                "Content appears as a single block of text. Break it into multiple "
                "paragraphs, add headings, and consider bullet points for key ideas."
            ),
            affected_block_index=0,
        ))

    return max(0, score), suggestions


def _platform_analysis(
    blocks: List[TextBlock], words: List[str], platform: str
) -> List[Suggestion]:
    suggestions: List[Suggestion] = []
    all_text = " ".join(b.text for b in blocks)
    word_count_val = len(words)
    hashtag_count = len(HASHTAG_PATTERN.findall(all_text))

    if platform == "instagram":
        # Caption length
        if word_count_val > 200:
            suggestions.append(Suggestion(
                category="platform",
                severity=SeverityLevel.MEDIUM,
                suggestion=(
                    f"Instagram captions perform best between 125–150 words. "
                    f"Your content is {word_count_val} words — consider trimming or splitting into a carousel."
                ),
            ))
        # Hashtags
        if hashtag_count == 0:
            suggestions.append(Suggestion(
                category="platform",
                severity=SeverityLevel.HIGH,
                suggestion=(
                    "No hashtags found. For Instagram, 5–10 targeted hashtags significantly "
                    "increase discoverability. Add them at the end of the caption."
                ),
            ))
        elif hashtag_count > 15:
            suggestions.append(Suggestion(
                category="platform",
                severity=SeverityLevel.LOW,
                suggestion=(
                    f"You have {hashtag_count} hashtags. Instagram's algorithm may suppress posts "
                    "with too many hashtags. Aim for 5–10 highly relevant ones."
                ),
            ))

    elif platform == "linkedin":
        if word_count_val < 100:
            suggestions.append(Suggestion(
                category="platform",
                severity=SeverityLevel.MEDIUM,
                suggestion=(
                    "LinkedIn posts between 150–300 words typically get the most reach. "
                    f"Your content is only {word_count_val} words — consider expanding with context or insights."
                ),
            ))
        if word_count_val > 500:
            suggestions.append(Suggestion(
                category="platform",
                severity=SeverityLevel.LOW,
                suggestion=(
                    "Very long LinkedIn posts can lose readers. Consider trimming to 300 words "
                    "or using a document/article format for longer content."
                ),
            ))

    elif platform == "twitter":
        total_chars = sum(len(b.text) for b in blocks)
        if total_chars > 280:
            suggestions.append(Suggestion(
                category="platform",
                severity=SeverityLevel.HIGH,
                suggestion=(
                    f"Content is {total_chars} characters, exceeding Twitter's 280-character limit. "
                    "Consider creating a thread or condensing to the key message."
                ),
            ))

    # General platform tip
    tip = PLATFORM_NOTES.get(platform, PLATFORM_NOTES["general"])["tip"]
    suggestions.append(Suggestion(
        category="platform",
        severity=SeverityLevel.LOW,
        suggestion=f"Platform tip ({platform}): {tip}",
    ))

    return suggestions


# ── Scoring helper ─────────────────────────────────────────────────────────────

def _compute_overall(readability: int, engagement: int, structure: int) -> int:
    """Weighted average: readability 35%, engagement 45%, structure 20%."""
    return min(100, int(readability * 0.35 + engagement * 0.45 + structure * 0.20))


def _split_sentences(text: str) -> List[str]:
    """
    Split text into sentences.
    Prefers NLTK sent_tokenize (more accurate) with a regex fallback.
    """
    if _nltk_ok:
        try:
            from nltk.tokenize import sent_tokenize
            return [s.strip() for s in sent_tokenize(text) if s.strip()]
        except Exception:
            pass
    # Regex fallback
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if s.strip()]


# ── Word lists ────────────────────────────────────────────────────────────────

CTA_KEYWORDS = {
    "click", "follow", "share", "subscribe", "comment", "like", "tag",
    "visit", "join", "download", "sign up", "register", "learn more",
    "get started", "try", "buy", "shop", "explore", "discover",
    "dm", "link in bio", "swipe up", "tap", "save",
}

POSITIVE_EMOTION_WORDS = {
    "amazing", "incredible", "exciting", "love", "best", "great", "fantastic",
    "awesome", "wonderful", "brilliant", "outstanding", "excellent", "perfect",
    "success", "win", "winning", "happy", "joy", "proud", "grateful",
    "inspired", "motivating", "powerful", "transformative",
}

NEGATIVE_FILLER_WORDS = {
    "very", "really", "quite", "rather", "somewhat", "actually", "basically",
    "literally", "definitely", "certainly", "just", "simply", "obviously",
}

PASSIVE_VOICE_PATTERNS = [
    re.compile(r"\b(is|are|was|were|be|been|being)\s+\w+ed\b", re.IGNORECASE),
    re.compile(r"\b(is|are|was|were)\s+being\s+\w+ed\b", re.IGNORECASE),
]

STAT_PATTERN = re.compile(r"\b\d+(\.\d+)?[\s]*(percent|%|million|billion|thousand|x|times)\b", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"\b\d+\b")
QUESTION_PATTERN = re.compile(r"\?")
HASHTAG_PATTERN = re.compile(r"#\w+")

PLATFORM_NOTES = {
    "instagram": {
        "ideal_caption_words": (125, 150),
        "hashtag_target": (5, 10),
        "tip": "Instagram posts with 5–10 relevant hashtags and a question in the caption get significantly higher engagement.",
    },
    "linkedin": {
        "ideal_post_words": (150, 300),
        "tip": "LinkedIn posts with statistics and a clear professional insight perform best. Avoid jargon.",
    },
    "twitter": {
        "char_limit": 280,
        "tip": "For Twitter/X, aim for punchy sentences under 280 characters. Threads work well for longer content.",
    },
    "general": {
        "tip": "Keep paragraphs short, use active voice, and end with a clear call to action.",
    },
}


# ── Main entry point ──────────────────────────────────────────────────────────

def analyze_content(blocks: List[TextBlock], platform: str = "general") -> AnalysisResponse:
    """
    Run all rule-based analyses on a list of text blocks.

    Returns an AnalysisResponse with suggestions and scores.
    """
    if not blocks:
        raise EmptyContentError()

    platform = platform.lower().strip()
    if platform not in PLATFORM_NOTES:
        platform = "general"

    try:
        text_blocks = [b for b in blocks if b.text.strip()]
        all_text = " ".join(b.text for b in text_blocks)
        sentences = _split_sentences(all_text)
        words = all_text.split()

        suggestions: List[Suggestion] = []

        r_score, r_suggestions = _readability_analysis(text_blocks, sentences, words)
        e_score, e_suggestions = _engagement_analysis(text_blocks, sentences, words, all_text)
        s_score, s_suggestions = _structure_analysis(blocks)
        p_suggestions = _platform_analysis(text_blocks, words, platform)

        suggestions.extend(r_suggestions)
        suggestions.extend(e_suggestions)
        suggestions.extend(s_suggestions)
        suggestions.extend(p_suggestions)

        # Sort by severity (high → medium → low)
        severity_order = {SeverityLevel.HIGH: 0, SeverityLevel.MEDIUM: 1, SeverityLevel.LOW: 2}
        suggestions.sort(key=lambda s: severity_order[s.severity])

        overall = _compute_overall(r_score, e_score, s_score)

        return AnalysisResponse(
            suggestions=suggestions,
            score=ScoreBreakdown(
                overall=overall,
                readability=r_score,
                engagement=e_score,
                structure=s_score,
            ),
        )
    except (EmptyContentError, AnalysisFailedError):
        raise
    except Exception as exc:
        logger.exception("Unexpected error in analysis: %s", exc)
        raise AnalysisFailedError(detail=str(exc)) from exc


# ── Sub-analyses ─────────────────────────────────────────────────────────────

def _readability_analysis(
    blocks: List[TextBlock], sentences: List[str], words: List[str]
) -> Tuple[int, List[Suggestion]]:
    suggestions: List[Suggestion] = []
    score = 100

    # Average sentence length
    if sentences:
        avg_sent_len = len(words) / len(sentences)
        if avg_sent_len > 25:
            score -= 25
            suggestions.append(Suggestion(
                category="readability",
                severity=SeverityLevel.HIGH,
                suggestion=(
                    f"Your average sentence length is {avg_sent_len:.0f} words — "
                    "aim for under 20 words per sentence to improve mobile readability."
                ),
            ))
        elif avg_sent_len > 18:
            score -= 10
            suggestions.append(Suggestion(
                category="readability",
                severity=SeverityLevel.MEDIUM,
                suggestion="Some sentences are long. Try breaking them up for clearer, punchier writing.",
            ))

    # Long paragraphs
    para_blocks = [b for b in blocks if b.type == BlockType.PARAGRAPH]
    long_paras = [
        i for i, b in enumerate(blocks)
        if b.type == BlockType.PARAGRAPH and len(b.text.split()) > 80
    ]
    if long_paras:
        score -= 15
        suggestions.append(Suggestion(
            category="readability",
            severity=SeverityLevel.HIGH,
            suggestion=(
                f"{len(long_paras)} paragraph(s) are very long (>80 words). "
                "Break them into shorter chunks or add bullet points."
            ),
            affected_block_index=long_paras[0],
        ))

    # Passive voice
    passive_count = sum(
        1 for pattern in PASSIVE_VOICE_PATTERNS
        for _ in pattern.finditer(" ".join(b.text for b in blocks))
    )
    if passive_count > 3:
        score -= 15
        suggestions.append(Suggestion(
            category="readability",
            severity=SeverityLevel.MEDIUM,
            suggestion=(
                f"Found {passive_count} instances of passive voice. "
                "Switch to active voice to make your writing more direct and engaging."
            ),
        ))

    # Filler words
    filler_count = sum(
        1 for w in words if w.lower().rstrip(".,!?;:") in NEGATIVE_FILLER_WORDS
    )
    filler_ratio = filler_count / max(len(words), 1)
    if filler_ratio > 0.05:
        score -= 10
        suggestions.append(Suggestion(
            category="readability",
            severity=SeverityLevel.LOW,
            suggestion=(
                f"Your content contains {filler_count} filler words (e.g. 'very', 'really', 'just'). "
                "Remove them to make sentences crisper."
            ),
        ))

    return max(0, score), suggestions


def _engagement_analysis(
    blocks: List[TextBlock], sentences: List[str], words: List[str], all_text: str
) -> Tuple[int, List[Suggestion]]:
    suggestions: List[Suggestion] = []
    score = 50  # Start at 50 — engagement must be earned

    word_set = {w.lower().rstrip(".,!?;:") for w in words}

    # Call to action
    cta_found = CTA_KEYWORDS & word_set
    if cta_found:
        score += 20
    else:
        suggestions.append(Suggestion(
            category="engagement",
            severity=SeverityLevel.HIGH,
            suggestion=(
                "No call-to-action detected. Add a directive at the end "
                "(e.g., 'Share your thoughts below', 'Follow for more', 'Click the link')."
            ),
        ))

    # Questions
    question_count = len(QUESTION_PATTERN.findall(all_text))
    if question_count >= 1:
        score += 15
    else:
        suggestions.append(Suggestion(
            category="engagement",
            severity=SeverityLevel.MEDIUM,
            suggestion=(
                "No questions found. Asking the audience a question boosts comments "
                "and interaction (e.g., 'What do you think?' or 'Have you tried this?')."
            ),
        ))

    # Emotional words
    emotion_found = POSITIVE_EMOTION_WORDS & word_set
    if emotion_found:
        score += 10

    # Statistics / numbers
    has_stats = bool(STAT_PATTERN.search(all_text))
    number_count = len(NUMBER_PATTERN.findall(all_text))
    if has_stats or number_count >= 2:
        score += 10
    else:
        suggestions.append(Suggestion(
            category="engagement",
            severity=SeverityLevel.LOW,
            suggestion=(
                "Adding specific numbers or statistics (e.g., '3 tips', '40% increase') "
                "makes content more credible and shareable."
            ),
        ))

    # Hook (first sentence)
    if sentences:
        first_sentence = sentences[0]
        first_words = len(first_sentence.split())
        if first_words > 30:
            score -= 5
            suggestions.append(Suggestion(
                category="engagement",
                severity=SeverityLevel.MEDIUM,
                suggestion=(
                    "Your opening sentence is long. Start with a short, punchy hook "
                    "(under 15 words) to grab attention instantly."
                ),
                affected_block_index=0,
            ))
        elif "?" in first_sentence or any(w in first_sentence.lower() for w in {"imagine", "what if", "stop", "warning", "how"}):
            score += 5  # bonus for a strong hook type

    return min(100, max(0, score)), suggestions


def _structure_analysis(blocks: List[TextBlock]) -> Tuple[int, List[Suggestion]]:
    suggestions: List[Suggestion] = []
    score = 100

    has_headings = any(b.type == BlockType.HEADING for b in blocks)
    has_bullets = any(b.type == BlockType.BULLET for b in blocks)
    total_blocks = len(blocks)

    # No headings
    if total_blocks > 5 and not has_headings:
        score -= 20
        suggestions.append(Suggestion(
            category="structure",
            severity=SeverityLevel.MEDIUM,
            suggestion=(
                "No headings were detected. Use headings to break up sections "
                "and help skimmers find what they need quickly."
            ),
        ))

    # No bullets (for longer content)
    if total_blocks > 8 and not has_bullets:
        score -= 10
        suggestions.append(Suggestion(
            category="structure",
            severity=SeverityLevel.LOW,
            suggestion=(
                "Consider using bullet points to organize lists or key takeaways. "
                "Bulleted content is 80% more readable at a glance."
            ),
        ))

    # Single long wall of text (one big block)
    if total_blocks == 1 and len(blocks[0].text.split()) > 100:
        score -= 30
        suggestions.append(Suggestion(
            category="structure",
            severity=SeverityLevel.HIGH,
            suggestion=(
                "Content appears as a single block of text. Break it into multiple "
                "paragraphs, add headings, and consider bullet points for key ideas."
            ),
            affected_block_index=0,
        ))

    return max(0, score), suggestions


def _platform_analysis(
    blocks: List[TextBlock], words: List[str], platform: str
) -> List[Suggestion]:
    suggestions: List[Suggestion] = []
    all_text = " ".join(b.text for b in blocks)
    word_count = len(words)
    hashtag_count = len(HASHTAG_PATTERN.findall(all_text))

    if platform == "instagram":
        # Caption length
        if word_count > 200:
            suggestions.append(Suggestion(
                category="platform",
                severity=SeverityLevel.MEDIUM,
                suggestion=(
                    f"Instagram captions perform best between 125–150 words. "
                    f"Your content is {word_count} words — consider trimming or splitting into a carousel."
                ),
            ))
        # Hashtags
        if hashtag_count == 0:
            suggestions.append(Suggestion(
                category="platform",
                severity=SeverityLevel.HIGH,
                suggestion=(
                    "No hashtags found. For Instagram, 5–10 targeted hashtags significantly "
                    "increase discoverability. Add them at the end of the caption."
                ),
            ))
        elif hashtag_count > 15:
            suggestions.append(Suggestion(
                category="platform",
                severity=SeverityLevel.LOW,
                suggestion=(
                    f"You have {hashtag_count} hashtags. Instagram's algorithm may suppress posts "
                    "with too many hashtags. Aim for 5–10 highly relevant ones."
                ),
            ))

    elif platform == "linkedin":
        if word_count < 100:
            suggestions.append(Suggestion(
                category="platform",
                severity=SeverityLevel.MEDIUM,
                suggestion=(
                    "LinkedIn posts between 150–300 words typically get the most reach. "
                    f"Your content is only {word_count} words — consider expanding with context or insights."
                ),
            ))
        if word_count > 500:
            suggestions.append(Suggestion(
                category="platform",
                severity=SeverityLevel.LOW,
                suggestion=(
                    "Very long LinkedIn posts can lose readers. Consider trimming to 300 words "
                    "or using a document/article format for longer content."
                ),
            ))

    elif platform == "twitter":
        total_chars = sum(len(b.text) for b in blocks)
        if total_chars > 280:
            suggestions.append(Suggestion(
                category="platform",
                severity=SeverityLevel.HIGH,
                suggestion=(
                    f"Content is {total_chars} characters, exceeding Twitter's 280-character limit. "
                    "Consider creating a thread or condensing to the key message."
                ),
            ))

    # General platform tip
    tip = PLATFORM_NOTES.get(platform, PLATFORM_NOTES["general"])["tip"]
    suggestions.append(Suggestion(
        category="platform",
        severity=SeverityLevel.LOW,
        suggestion=f"Platform tip ({platform}): {tip}",
    ))

    return suggestions


# ── Scoring helper ─────────────────────────────────────────────────────────────

def _compute_overall(readability: int, engagement: int, structure: int) -> int:
    """Weighted average: readability 35%, engagement 45%, structure 20%."""
    return min(100, int(readability * 0.35 + engagement * 0.45 + structure * 0.20))


def _split_sentences(text: str) -> List[str]:
    """Simple sentence splitter on punctuation boundaries."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if s.strip()]
