"""Matcher tests — run fully offline (no LLM, no network)."""

from jobagent.matcher import keyword_score, rank
from jobagent.models import Job, Profile


def _profile():
    return Profile(skills=["python", "django", "postgres"], preferences={"keywords": ["backend"]})


def test_keyword_score_rewards_overlap():
    match = Job(title="Backend Python Engineer", company="Acme", url="http://a",
                source="test", description="Django and Postgres experience required.")
    miss = Job(title="Graphic Designer", company="Beta", url="http://b",
               source="test", description="Figma and Illustrator.")
    assert keyword_score(_profile(), match) > keyword_score(_profile(), miss)


def test_keyword_score_zero_without_terms():
    empty = Profile()
    job = Job(title="Anything", company="X", url="http://x", source="test")
    assert keyword_score(empty, job) == 0.0


def test_rank_orders_best_first_without_llm():
    jobs = [
        Job(title="Graphic Designer", company="Beta", url="http://b", source="test"),
        Job(title="Senior Python Backend Developer", company="Acme", url="http://a",
            source="test", description="Django, Postgres, REST APIs."),
    ]
    ranked = rank(_profile(), jobs, llm=None)
    assert ranked[0].job.company == "Acme"
    assert ranked[0].score >= ranked[1].score
    assert ranked[0].method == "keyword"
