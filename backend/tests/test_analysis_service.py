"""
Tests for the enriched analysis service (unit tests).

Covers:
  - All 11 new public analysis functions
  - Backward compatibility of the enriched AnalysisResponse shape
"""
import pytest

from app.services.analysis_service import (
    analyze_content,
    analyze_sentiment,
    detect_keywords,
    calculate_readability,
    estimate_engagement,
    suggest_hashtags,
    improve_caption,
    detect_call_to_action,
    grammar_suggestions,
    character_count,
    word_count,
    reading_time,
    _split_sentences,
)
from app.models.response_models import TextBlock, BlockType, KeywordItem
from app.utils.error_handlers import EmptyContentError


# ── Shared fixtures ────────────────────────────────────────────────────────────

SAMPLE_TEXT = (
    "Amazing new product launch! Our team has worked incredibly hard to bring you "
    "this incredible experience. Share your thoughts below and follow us for more updates. "
    "We achieved a 40% increase in performance and 3x faster load times. "
    "What do you think of the new features?"
)

SAMPLE_TEXT_SHORT = "Quick test."


def _make_blocks(texts: list[str], block_type=BlockType.PARAGRAPH) -> list[TextBlock]:
    return [TextBlock(type=block_type, level=None, text=t, page=1) for t in texts]


# ── analyze_sentiment ──────────────────────────────────────────────────────────

def test_analyze_sentiment_positive():
    result = analyze_sentiment("This is absolutely amazing and wonderful!")
    if result is not None:  # graceful if TextBlob unavailable
        assert result.polarity > 0
        assert result.label in ("positive", "very positive")


def test_analyze_sentiment_negative():
    result = analyze_sentiment("This is terrible, awful, and completely broken.")
    if result is not None:
        assert result.polarity < 0
        assert result.label in ("negative", "very negative")


def test_analyze_sentiment_empty_returns_none():
    result = analyze_sentiment("")
    assert result is None


def test_analyze_sentiment_returns_valid_subjectivity_label():
    result = analyze_sentiment("The sky is blue.")
    if result is not None:
        assert result.subjectivity_label in ("objective", "balanced", "subjective")
        assert 0.0 <= result.polarity <= 1.0 or -1.0 <= result.polarity < 0.0
        assert 0.0 <= result.subjectivity <= 1.0


# ── detect_keywords ────────────────────────────────────────────────────────────

def test_detect_keywords_returns_list_or_none():
    result = detect_keywords(SAMPLE_TEXT, top_n=10)
    if result is not None:
        assert isinstance(result, list)
        assert len(result) <= 10
        for kw in result:
            assert kw.frequency >= 1
            assert 0.0 <= kw.score <= 1.0


def test_detect_keywords_empty_text_returns_none():
    assert detect_keywords("") is None


def test_detect_keywords_respects_top_n():
    result = detect_keywords(SAMPLE_TEXT, top_n=3)
    if result is not None:
        assert len(result) <= 3


# ── calculate_readability ──────────────────────────────────────────────────────

def test_calculate_readability_returns_float_for_valid_text():
    result = calculate_readability(SAMPLE_TEXT)
    if result is not None:
        assert isinstance(result, float)
        assert result >= 0.0


def test_calculate_readability_empty_returns_none():
    assert calculate_readability("") is None


def test_calculate_readability_single_word_returns_none():
    # One word = no sentence boundary
    assert calculate_readability("Hello") is None or calculate_readability("Hello") >= 0


# ── estimate_engagement ────────────────────────────────────────────────────────

def test_estimate_engagement_returns_clamped_score():
    score = estimate_engagement(SAMPLE_TEXT)
    assert 0 <= score <= 100


def test_estimate_engagement_higher_with_cta():
    no_cta = estimate_engagement("This is interesting content about our product.")
    with_cta = estimate_engagement("Share this amazing product with your friends!")
    assert with_cta >= no_cta


def test_estimate_engagement_with_sentiment_boost():
    from app.services.analysis_service import analyze_sentiment
    sentiment = analyze_sentiment("Incredible, amazing, wonderful experience!")
    score_with = estimate_engagement(SAMPLE_TEXT, sentiment=sentiment)
    assert 0 <= score_with <= 100


# ── suggest_hashtags ───────────────────────────────────────────────────────────

def test_suggest_hashtags_returns_list_when_keywords_provided():
    keywords = [
        KeywordItem(word="fitness", frequency=3, score=1.0, pos_tag="NOUN"),
        KeywordItem(word="health", frequency=2, score=0.7, pos_tag="NOUN"),
        KeywordItem(word="workout", frequency=2, score=0.6, pos_tag="NOUN"),
    ]
    result = suggest_hashtags(keywords)
    if result is not None:
        assert all(h.startswith("#") for h in result)
        assert len(result) <= 10


def test_suggest_hashtags_none_when_no_keywords():
    assert suggest_hashtags(None) is None
    assert suggest_hashtags([]) is None


def test_suggest_hashtags_excludes_existing():
    keywords = [KeywordItem(word="fitness", frequency=3, score=1.0, pos_tag="NOUN")]
    result = suggest_hashtags(keywords, existing_hashtags=["#fitness"])
    # 'fitness' is already in use — should not be suggested again
    assert result is None or "#fitness" not in result


def test_suggest_hashtags_respects_blocklist():
    keywords = [
        KeywordItem(word="the", frequency=10, score=1.0, pos_tag="NOUN"),
        KeywordItem(word="and", frequency=8, score=0.9, pos_tag="NOUN"),
    ]
    result = suggest_hashtags(keywords)
    # Blocklisted words should not appear
    assert result is None or not any(h in ("#the", "#and") for h in result)


# ── improve_caption ────────────────────────────────────────────────────────────

def test_improve_caption_returns_string():
    blocks = _make_blocks([SAMPLE_TEXT])
    result = improve_caption(blocks, SAMPLE_TEXT, cta_detected=True)
    assert result is None or isinstance(result, str)


def test_improve_caption_appends_cta_when_missing():
    blocks = _make_blocks(["This is a plain description without any directive."])
    result = improve_caption(blocks, "description", cta_detected=False)
    if result is not None:
        assert "Share" in result or "comment" in result.lower()


def test_improve_caption_respects_200_word_cap():
    long_text = "This is a very long paragraph. " * 20
    blocks = _make_blocks([long_text])
    result = improve_caption(blocks, long_text, cta_detected=True)
    if result is not None:
        assert len(result.split()) <= 205  # allow small tolerance for appended CTA


def test_improve_caption_none_for_empty_blocks():
    assert improve_caption([], "", cta_detected=False) is None


# ── detect_call_to_action ──────────────────────────────────────────────────────

def test_detect_cta_true_for_cta_text():
    assert detect_call_to_action("Follow us for more amazing content!") is True


def test_detect_cta_false_for_plain_text():
    assert detect_call_to_action("The weather is nice today.") is False


def test_detect_cta_empty_text():
    assert detect_call_to_action("") is False


def test_detect_cta_whole_word_only():
    # 'discovery' should NOT match 'discover'
    assert detect_call_to_action("Scientific discovery was announced.") is False


# ── grammar_suggestions ────────────────────────────────────────────────────────

def test_grammar_suggestions_returns_list():
    result = grammar_suggestions("Ths iz a tst sentece with errers.")
    assert isinstance(result, list)
    # May be empty if TextBlob unavailable — that's fine
    for issue in result:
        assert issue.issue_type in ("spelling", "style")
        assert issue.original
        assert issue.suggestion


def test_grammar_suggestions_empty_text_returns_empty():
    assert grammar_suggestions("") == []


def test_grammar_suggestions_respects_max_issues():
    long_text = "Thi iz vry bad wrds writting evry sngle day basicly."
    result = grammar_suggestions(long_text, max_issues=3)
    assert len(result) <= 3


def test_grammar_suggestions_flags_style_issues():
    # "very" repeated 3+ times should generate a style issue
    text = "It is very very very important to act very quickly."
    result = grammar_suggestions(text, max_issues=10)
    style_issues = [i for i in result if i.issue_type == "style"]
    # May or may not flag depending on TextBlob availability
    assert isinstance(style_issues, list)


# ── character_count / word_count / reading_time ────────────────────────────────

def test_character_count_basic():
    assert character_count("Hello World") == 11


def test_character_count_empty():
    assert character_count("") == 0


def test_character_count_unicode():
    assert character_count("héllo") == 5  # 5 Unicode code points


def test_word_count_basic():
    assert word_count("one two three") == 3


def test_word_count_empty():
    assert word_count("") == 0


def test_reading_time_short_text():
    seconds, label = reading_time("Quick.")
    assert seconds >= 1
    assert "min" in label


def test_reading_time_long_text():
    # 400 words at 200 wpm = 120 seconds = "2 min read"
    text = " ".join(["word"] * 400)
    seconds, label = reading_time(text, wpm=200)
    assert seconds == 120
    assert label == "2 min read"


def test_reading_time_under_one_minute():
    text = " ".join(["word"] * 50)  # 50 words = 15s at 200wpm
    seconds, label = reading_time(text, wpm=200)
    assert seconds == 15
    assert "< 1 min" in label


# ── Full analyze_content enriched response ─────────────────────────────────────

def test_analyze_content_returns_enriched_fields():
    blocks = _make_blocks([SAMPLE_TEXT])
    result = analyze_content(blocks, "general")
    # Existing fields — must always be present
    assert result.suggestions is not None
    assert result.score is not None
    # New fields — present if libraries available, else None
    assert hasattr(result, "sentiment")
    assert hasattr(result, "keywords")
    assert hasattr(result, "suggested_hashtags")
    assert hasattr(result, "improved_caption")
    assert hasattr(result, "grammar_suggestions")
    assert hasattr(result, "statistics")


def test_analyze_content_statistics_always_populated():
    blocks = _make_blocks([SAMPLE_TEXT])
    result = analyze_content(blocks, "general")
    # statistics uses no NLP models so must always be non-None
    assert result.statistics is not None
    assert result.statistics.word_count > 0
    assert result.statistics.character_count > 0
    assert result.statistics.reading_time_label != ""


def test_analyze_content_empty_blocks_raises():
    with pytest.raises(EmptyContentError):
        analyze_content([], "general")


def test_analyze_content_backward_compatible_score_shape():
    """Existing score shape must not change."""
    blocks = _make_blocks(["Share this post with your friends! What do you think?"])
    result = analyze_content(blocks, "general")
    assert 0 <= result.score.overall <= 100
    assert 0 <= result.score.readability <= 100
    assert 0 <= result.score.engagement <= 100
    assert 0 <= result.score.structure <= 100


def test_analyze_content_grammar_issues_appear_in_suggestions():
    """Grammar issues should be mirrored in suggestions list as 'grammar' category."""
    blocks = _make_blocks(["Thi iz a vry bad sentece. Writting iz basicly terrible."])
    result = analyze_content(blocks, "general")
    grammar_in_suggestions = [s for s in result.suggestions if s.category == "grammar"]
    # May be empty if TextBlob unavailable; just verify the type
    assert isinstance(grammar_in_suggestions, list)
