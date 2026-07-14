from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class BlockType(str, Enum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    BULLET = "bullet"
    UNKNOWN = "unknown"


class TextBlock(BaseModel):
    type: BlockType
    level: Optional[int] = Field(None, ge=1, le=6, description="Heading level (1–6), null for non-headings")
    text: str
    page: int = Field(ge=1)


class ExtractionMetadata(BaseModel):
    processing_time_ms: int
    character_count: int
    ocr_confidence: Optional[float] = Field(None, ge=0.0, le=100.0)


class ExtractionContent(BaseModel):
    blocks: List[TextBlock]


class ExtractionResponse(BaseModel):
    filename: str
    file_type: str  # "pdf" | "image"
    page_count: int
    content: ExtractionContent
    metadata: ExtractionMetadata


# ── Analysis Models ──────────────────────────────────────────────────────────

class SeverityLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Suggestion(BaseModel):
    category: str  # "readability" | "engagement" | "structure" | "platform" | "grammar"
    severity: SeverityLevel
    suggestion: str
    affected_block_index: Optional[int] = None


class ScoreBreakdown(BaseModel):
    overall: int = Field(ge=0, le=100)
    readability: int = Field(ge=0, le=100)
    engagement: int = Field(ge=0, le=100)
    structure: int = Field(ge=0, le=100)


class AnalysisRequest(BaseModel):
    blocks: List[TextBlock]
    context: dict = Field(default_factory=lambda: {"platform": "general"})


# ── Rich analysis extension models ───────────────────────────────────────────

class SentimentResult(BaseModel):
    """TextBlob polarity/subjectivity scores + a human-readable label."""
    polarity: float = Field(
        description="Sentiment polarity: -1.0 (very negative) to 1.0 (very positive)."
    )
    subjectivity: float = Field(
        description="Subjectivity: 0.0 (objective/factual) to 1.0 (very subjective/opinionated)."
    )
    label: str = Field(
        description="Human-readable label: 'very positive' | 'positive' | 'neutral' | 'negative' | 'very negative'."
    )
    subjectivity_label: str = Field(
        description="'objective' | 'balanced' | 'subjective'."
    )


class KeywordItem(BaseModel):
    """A significant keyword/keyphrase extracted from the content."""
    word: str
    frequency: int = Field(ge=1, description="Number of occurrences in the text.")
    score: float = Field(ge=0.0, le=1.0, description="Normalised relevance score.")
    pos_tag: str = Field(description="spaCy part-of-speech tag (NOUN, PROPN, ADJ, etc.).")


class GrammarIssue(BaseModel):
    """A single basic spelling or style issue detected by TextBlob."""
    original: str
    suggestion: str
    issue_type: str = Field(description="'spelling' | 'style'.")


class ContentStatistics(BaseModel):
    """Lightweight content metrics derived without NLP models."""
    character_count: int
    word_count: int
    sentence_count: int
    paragraph_count: int
    reading_time_seconds: int
    reading_time_label: str = Field(
        description="Human-readable reading time, e.g. '< 1 min' or '2 min read'."
    )
    average_words_per_sentence: float
    cta_detected: bool
    question_count: int
    hashtag_count: int
    emoji_count: int


class AnalysisResponse(BaseModel):
    # ── Existing fields (unchanged) ──────────────────────────────────────────
    suggestions: List[Suggestion]
    score: ScoreBreakdown

    # ── New enriched fields (all Optional for backward compatibility) ─────────
    sentiment: Optional[SentimentResult] = Field(
        None,
        description="TextBlob sentiment analysis result.",
    )
    keywords: Optional[List[KeywordItem]] = Field(
        None,
        description="Top keywords/keyphrases extracted using NLTK + spaCy NER.",
    )
    suggested_hashtags: Optional[List[str]] = Field(
        None,
        description="Hashtag suggestions derived from extracted keywords.",
    )
    improved_caption: Optional[str] = Field(
        None,
        description="A rule-based rewrite of the first paragraph: shorter sentences, active voice hint, CTA appended if missing.",
    )
    grammar_suggestions: Optional[List[GrammarIssue]] = Field(
        None,
        description="Basic spelling/style issues found by TextBlob (max 10 returned).",
    )
    statistics: Optional[ContentStatistics] = Field(
        None,
        description="Lightweight content statistics: word count, reading time, CTA detection, etc.",
    )


# ── Health Model ─────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str

