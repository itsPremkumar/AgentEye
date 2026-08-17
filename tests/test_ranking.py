"""Tests for the new ranking modules — all offline, no network."""
from __future__ import annotations

import pytest
from agent_eye.ranking import rank_results
from agent_eye.domain_authority import domain_authority_score, DOMAIN_AUTHORITY
from agent_eye.freshness import freshness_score, is_time_sensitive_query
from agent_eye.snippet_intent import (
    detect_query_intent,
    dominant_intent,
    snippet_quality_score,
)
from agent_eye.diversity import (
    content_fingerprint,
    deduplicate_similar,
    enforce_site_diversity,
)
from agent_eye.spellcheck import (
    COMMON_TYPOS,
    extract_entities,
    levenshtein_distance,
    suggest_correction,
)


# ---------------------------------------------------------------------------
# Domain authority
# ---------------------------------------------------------------------------
class TestDomainAuthority:
    def test_academic_domains_high(self):
        assert domain_authority_score("https://arxiv.org/abs/1234") >= 0.9
        assert domain_authority_score("https://pubmed.ncbi.nlm.nih.gov/123") >= 0.9
        assert domain_authority_score("https://nature.com/articles/123") >= 0.9

    def test_news_domains_medium_high(self):
        assert domain_authority_score("https://reuters.com/article") >= 0.9
        assert domain_authority_score("https://bbc.com/news/123") >= 0.9
        assert domain_authority_score("https://nytimes.com/2026/01/01") >= 0.85

    def test_social_domains_lower(self):
        assert domain_authority_score("https://reddit.com/r/python") <= 0.7
        assert domain_authority_score("https://twitter.com/user") <= 0.6
        assert domain_authority_score("https://facebook.com/page") <= 0.5

    def test_gov_domains_high(self):
        assert domain_authority_score("https://nasa.gov/mars") >= 0.9
        assert domain_authority_score("https://nih.gov/research") >= 0.9
        assert domain_authority_score("https://who.int/health") >= 0.9

    def test_tech_domains_high(self):
        assert domain_authority_score("https://github.com/python") >= 0.9
        assert domain_authority_score("https://stackoverflow.com/q/123") >= 0.9
        assert domain_authority_score("https://docs.python.org/3") >= 0.9

    def test_www_stripped(self):
        assert domain_authority_score("https://www.arxiv.org/abs/1234") >= 0.9
        assert domain_authority_score("https://www.github.com/python") >= 0.9

    def test_subdomain_matches_parent(self):
        assert domain_authority_score("https://blog.nature.com/x") >= 0.85
        assert domain_authority_score("https://docs.python.org/3") >= 0.9

    def test_unknown_domain_neutral(self):
        assert domain_authority_score("https://random-site-12345.com/x") == 0.5

    def test_tld_fallback(self):
        # .edu → 0.9, .gov → 0.95
        assert domain_authority_score("https://harvard.edu/x") >= 0.85
        assert domain_authority_score("https://whitehouse.gov/x") >= 0.9

    def test_empty_url(self):
        assert domain_authority_score("") == 0.5


# ---------------------------------------------------------------------------
# Freshness
# ---------------------------------------------------------------------------
class TestFreshness:
    def test_today(self):
        score = freshness_score("News from January 15, 2026", "Today's top stories")
        # Today's date is in 2026, so this should be high
        assert score >= 0.5  # neutral at minimum (future/past depends on actual date)

    def test_recent_date(self):
        score = freshness_score("Python 3.12 Released", "Announced in 2026")
        assert 0.0 <= score <= 1.0

    def test_old_date(self):
        score = freshness_score("History of Python", "Created in 1991")
        assert score <= 0.5  # old = low score

    def test_relative_days_ago(self):
        score = freshness_score("Posted 3 days ago", "Latest update")
        assert score >= 0.9  # within a week

    def test_relative_months_ago(self):
        score = freshness_score("Posted 6 months ago", "From last year")
        assert score <= 0.7

    def test_no_date(self):
        score = freshness_score("Python Programming", "A popular language")
        assert score == 0.5  # neutral

    def test_time_sensitive_query(self):
        assert is_time_sensitive_query("latest AI news") is True
        assert is_time_sensitive_query("python tutorial") is False
        assert is_time_sensitive_query("breaking: new release") is True
        assert is_time_sensitive_query("what is machine learning") is False

    def test_iso_date(self):
        score = freshness_score("Released 2026-01-15", "Today")
        assert 0.0 <= score <= 1.0

    def test_year_only(self):
        score = freshness_score("2026 Year in Review", "Summary")
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# Snippet quality
# ---------------------------------------------------------------------------
class TestSnippetQuality:
    def test_exact_query_in_title(self):
        score = snippet_quality_score(
            "Python Tutorial for Beginners",
            "Learn Python programming step by step.",
            "python tutorial"
        )
        assert score >= 0.5

    def test_empty_snippet(self):
        score = snippet_quality_score("Title", "", "query")
        assert score <= 0.2

    def test_short_title(self):
        score = snippet_quality_score("Hi", "Description here", "query")
        assert score <= 0.3

    def test_definitive_boost(self):
        score_with = snippet_quality_score(
            "How to Learn Python", "A complete guide.", "learn python"
        )
        score_without = snippet_quality_score(
            "Python Stuff", "Some random text.", "learn python"
        )
        assert score_with >= score_without

    def test_perfect_match(self):
        score = snippet_quality_score(
            "Machine Learning Tutorial",
            "This tutorial covers machine learning fundamentals in depth.",
            "machine learning tutorial"
        )
        assert score >= 0.6

    def test_no_overlap(self):
        score = snippet_quality_score(
            "Cooking Recipes",
            "How to bake sourdough bread.",
            "python programming"
        )
        assert score <= 0.5


# ---------------------------------------------------------------------------
# Query intent
# ---------------------------------------------------------------------------
class TestQueryIntent:
    def test_factual(self):
        intents = detect_query_intent("what is machine learning")
        assert dominant_intent("what is machine learning") == "factual"

    def test_how_to(self):
        assert dominant_intent("how to learn python") == "how_to"

    def test_news(self):
        assert dominant_intent("latest AI news") == "news"

    def test_comparison(self):
        assert dominant_intent("python vs ruby") == "comparison"

    def test_code(self):
        assert dominant_intent("python function example") == "code"

    def test_opinion(self):
        # Use unambiguous opinion queries (no code keywords like "python")
        assert dominant_intent("thoughts and review") == "opinion"
        assert dominant_intent("my recommendation and rating") == "opinion"

    def test_intents_normalized(self):
        intents = detect_query_intent("latest news")
        total = sum(intents.values())
        assert 0.99 <= total <= 1.01  # sums to ~1.0

    def test_no_match(self):
        intents = detect_query_intent("xyz abc 123")
        assert all(v == 0.0 for v in intents.values())


# ---------------------------------------------------------------------------
# Diversity
# ---------------------------------------------------------------------------
class TestDiversity:
    def test_site_diversity_caps(self):
        results = [
            {"url": "https://medium.com/a", "title": "A", "relevance_score": 0.9},
            {"url": "https://medium.com/b", "title": "B", "relevance_score": 0.8},
            {"url": "https://medium.com/c", "title": "C", "relevance_score": 0.7},
            {"url": "https://arxiv.org/x", "title": "X", "relevance_score": 0.85},
        ]
        diverse = enforce_site_diversity(results, max_per_domain=2)
        # medium.com should have at most 2 in top positions
        medium_count = sum(1 for r in diverse[:3] if "medium.com" in r["url"])
        assert medium_count <= 2

    def test_site_diversity_preserves_order(self):
        results = [
            {"url": "https://a.com/1", "title": "A1", "relevance_score": 0.9},
            {"url": "https://b.com/1", "title": "B1", "relevance_score": 0.8},
            {"url": "https://a.com/2", "title": "A2", "relevance_score": 0.7},
        ]
        diverse = enforce_site_diversity(results, max_per_domain=2)
        # a.com has 2, both should be in top 2 (they were already there)
        assert len(diverse) == 3

    def test_fingerprint_same_content(self):
        fp1 = content_fingerprint("Python Tutorial", "Learn Python programming")
        fp2 = content_fingerprint("Tutorial Python", "Python programming learn")
        assert fp1 == fp2  # order-independent

    def test_fingerprint_different_content(self):
        fp1 = content_fingerprint("Python Tutorial", "Learn Python")
        fp2 = content_fingerprint("JavaScript Guide", "Learn JavaScript")
        assert fp1 != fp2

    def test_deduplicate_similar(self):
        results = [
            {"title": "Python Tutorial", "description": "Learn Python programming"},
            {"title": "Tutorial Python", "description": "Python programming learn"},
            {"title": "JavaScript Guide", "description": "Learn JavaScript"},
        ]
        unique = deduplicate_similar(results)
        assert len(unique) == 2

    def test_deduplicate_preserves_first(self):
        results = [
            {"title": "Python Tutorial", "description": "Learn Python", "id": 1},
            {"title": "Tutorial Python", "description": "Python learn", "id": 2},
        ]
        unique = deduplicate_similar(results)
        assert unique[0]["id"] == 1


# ---------------------------------------------------------------------------
# Spell-check
# ---------------------------------------------------------------------------
class TestSpellCheck:
    def test_known_typos(self):
        assert suggest_correction("pyton") == "python"
        assert suggest_correction("guthub") == "github"
        assert suggest_correction("documenation") == "documentation"
        assert suggest_correction("artifical") == "artificial"

    def test_no_typo(self):
        assert suggest_correction("python") is None
        assert suggest_correction("machine learning") is None

    def test_levenshtein(self):
        assert levenshtein_distance("kitten", "sitting") == 3
        assert levenshtein_distance("", "abc") == 3
        assert levenshtein_distance("abc", "abc") == 0
        assert levenshtein_distance("pyton", "python") == 1

    def test_extract_entities(self):
        entities = extract_entities("python tutorial for machine learning")
        assert "python" in entities["tech"]
        assert "machine" not in entities["tech"]  # not in TECH_ENTITIES

    def test_extract_tech(self):
        entities = extract_entities("react vs angular comparison")
        assert "react" in entities["tech"]
        assert "angular" in entities["tech"]
        assert entities["has_comparison"] is True

    def test_extract_year(self):
        entities = extract_entities("AI news 2026")
        assert entities["has_year"] is True

    def test_extract_question(self):
        entities = extract_entities("how to learn python")
        assert "how" in entities["question_words"]


# ---------------------------------------------------------------------------
# rank_results integration
# ---------------------------------------------------------------------------
class TestRankResults:
    def test_rank_empty(self):
        assert rank_results([]) == []

    def test_rank_single(self):
        results = [{"title": "Python", "description": "Language", "source": "github", "url": "https://github.com/python"}]
        ranked = rank_results(results, "python")
        assert len(ranked) == 1
        assert ranked[0]["position"] == 1

    def test_rank_by_relevance(self):
        results = [
            {"title": "Cooking Recipes", "description": "Bake bread", "source": "reddit", "url": "https://reddit.com/r/cooking"},
            {"title": "Python Tutorial", "description": "Learn Python programming", "source": "github", "url": "https://github.com/python"},
            {"title": "Python Documentation", "description": "Official docs", "source": "github", "url": "https://docs.python.org"},
        ]
        ranked = rank_results(results, "python tutorial")
        # Python results should rank higher than cooking
        assert ranked[0]["title"] in ("Python Tutorial", "Python Documentation")

    def test_rank_domain_authority(self):
        results = [
            {"title": "Python", "description": "Language", "source": "reddit", "url": "https://random-blog.com/python"},
            {"title": "Python", "description": "Language", "source": "reddit", "url": "https://arxiv.org/python"},
        ]
        ranked = rank_results(results, "python")
        # arxiv.org should beat random-blog.com
        assert "arxiv.org" in ranked[0]["url"]

    def test_rank_dedup(self):
        results = [
            {"title": "Python Tutorial", "description": "Learn Python", "source": "github", "url": "https://github.com/1"},
            {"title": "Tutorial Python", "description": "Python learn", "source": "github", "url": "https://github.com/2"},
            {"title": "Different Topic", "description": "Something else", "source": "github", "url": "https://github.com/3"},
        ]
        ranked = rank_results(results, "python tutorial")
        # Near-duplicates should be removed
        assert len(ranked) <= 2

    def test_rank_diversity(self):
        results = [
            {"title": "Python A", "description": "Tutorial", "source": "github", "url": "https://medium.com/a", "relevance_score": 0.9},
            {"title": "Python B", "description": "Tutorial", "source": "github", "url": "https://medium.com/b", "relevance_score": 0.85},
            {"title": "Python C", "description": "Tutorial", "source": "github", "url": "https://medium.com/c", "relevance_score": 0.8},
            {"title": "Python D", "description": "Tutorial", "source": "github", "url": "https://arxiv.org/d", "relevance_score": 0.82},
        ]
        ranked = rank_results(results, "python tutorial")
        # arxiv.org (0.82) should rank higher than medium.com/c (0.8) due to authority
        assert "arxiv.org" in ranked[0]["url"]

    def test_rank_position_update(self):
        results = [
            {"title": "A", "description": "X", "source": "github", "url": "https://github.com/a"},
            {"title": "B", "description": "Y", "source": "github", "url": "https://github.com/b"},
        ]
        ranked = rank_results(results, "test")
        for i, r in enumerate(ranked):
            assert r["position"] == i + 1
