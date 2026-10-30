"""
Phase 4 — Real NLP Service Tests.
Run with:   pytest tests/test_nlp_service.py -v
"""

import pytest

from app.services.nlp_service import NLPService

@pytest.fixture(scope="module")
def nlp():
    # Only load the model once for all tests to speed things up
    return NLPService(ontology_path="data/ontology/skills.json", model_name="en_core_web_sm")

def test_clean_text(nlp):
    dirty = "This   is \n a  test.\t"
    assert nlp.clean_text(dirty) == "This is a test."

def test_extract_skills_exact_match(nlp):
    text = "I have 5 years of experience with Python and Java."
    skills = nlp.extract_skills(text)
    assert "Python" in skills
    assert "Java" in skills
    assert len(skills) == 2

def test_extract_skills_synonyms(nlp):
    text = "I love natural language processing and working with a Vector DB."
    skills = nlp.extract_skills(text)
    assert "Natural Language Processing" in skills
    assert "Vector Database" in skills

def test_extract_skills_acronyms_cased_correctly(nlp):
    text = "We use aws and gcp to deploy our genai apps with llms."
    skills = nlp.extract_skills(text)
    assert "Amazon Web Services" in skills
    assert "Google Cloud Platform" in skills
    assert "Large Language Models" in skills
    assert "Generative Ai" in skills or "Generative AI" in skills

def test_extract_skills_empty_text(nlp):
    assert nlp.extract_skills("") == []

def test_extract_entities(nlp):
    text = "Microsoft is acquiring a startup for $50M in London."
    ents = nlp.extract_entities(text)
    assert "Microsoft" in ents.get("ORG", [])
    assert "London" in ents.get("GPE", [])
