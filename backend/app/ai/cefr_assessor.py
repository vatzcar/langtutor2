"""CEFR level definitions, topic mappings, and assessment utilities."""

from __future__ import annotations

CEFR_LEVELS: list[str] = ["A0", "A1", "A2", "B1", "B2", "C1"]

CEFR_TOPICS: dict[str, list[str]] = {
    "A0": [
        "Alphabet and pronunciation",
        "Basic greetings and farewells",
        "Numbers 1-20",
        "Self-introduction (name, age)",
        "Common classroom phrases",
        "Yes/no questions",
    ],
    "A1": [
        "Numbers and counting (20-100)",
        "Days of the week and months",
        "Family members",
        "Colors and basic adjectives",
        "Simple present tense",
        "Basic food and drink vocabulary",
        "Telling time",
        "Simple questions (who, what, where)",
    ],
    "A2": [
        "Past tense (regular verbs)",
        "Future tense (basic)",
        "Giving and following directions",
        "Shopping and prices",
        "Describing daily routines",
        "Weather and seasons",
        "Health and body parts",
        "Comparatives and superlatives",
    ],
    "B1": [
        "Past tense (irregular verbs)",
        "Conditional sentences (basic)",
        "Expressing opinions and preferences",
        "Travel and transportation",
        "Work and professions vocabulary",
        "Connecting ideas (because, although, however)",
        "Describing experiences and events",
    ],
    "B2": [
        "Subjunctive mood",
        "Complex conditional sentences",
        "Idiomatic expressions",
        "Formal vs informal register",
        "Debating and argumentation",
        "Abstract topics (culture, society)",
        "Passive voice in context",
        "Nuanced vocabulary (synonyms, connotation)",
    ],
    "C1": [
        "Advanced idiomatic and colloquial language",
        "Discourse markers and cohesion",
        "Humor, irony, and sarcasm",
        "Academic and professional writing style",
        "Regional dialects and variations",
        "Complex grammatical structures in speech",
    ],
}


def get_next_level(current: str) -> str | None:
    """Return the next CEFR level, or None if already at the highest."""
    try:
        idx = CEFR_LEVELS.index(current)
    except ValueError:
        return None
    if idx + 1 < len(CEFR_LEVELS):
        return CEFR_LEVELS[idx + 1]
    return None


def get_topics_for_level(level: str) -> list[str]:
    """Return the list of topics for a given CEFR level."""
    return CEFR_TOPICS.get(level, [])


def get_reinforcement_topics(current_level: str) -> list[str]:
    """Return all topics from levels below the current level for reinforcement."""
    topics: list[str] = []
    try:
        idx = CEFR_LEVELS.index(current_level)
    except ValueError:
        return topics
    for level in CEFR_LEVELS[:idx]:
        topics.extend(CEFR_TOPICS.get(level, []))
    return topics


ASSESSMENT_PROMPT = """\
You are a CEFR language assessment expert. Based on the conversation so far, \
evaluate the student's proficiency in the target language.

Respond with ONLY a valid JSON object in the following format — no extra text:

{
    "vocabulary": <0-100>,
    "grammar": <0-100>,
    "fluency": <0-100>,
    "comprehension": <0-100>,
    "overall_score": <0-100>,
    "determined_level": "<A0|A1|A2|B1|B2|C1>",
    "reasoning": "<brief explanation of the assessment>"
}

Scoring guidelines:
- **vocabulary** — range and accuracy of words used
- **grammar** — correctness and complexity of sentence structures
- **fluency** — natural flow, hesitation, and self-correction ability
- **comprehension** — understanding of questions and prompts
- **overall_score** — weighted average reflecting all dimensions
- **determined_level** — the CEFR level that best matches the overall score

Be fair but accurate. Do not inflate scores to be polite.\
"""
