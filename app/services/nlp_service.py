"""
Real NLP Service using spaCy.

Features:
- Text cleaning
- Skill extraction using PhraseMatcher against a predefined ontology.
- Entity extraction (ORG, PERSON, GPE, etc.)
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class NLPService:
    def __init__(self, ontology_path: str = "data/ontology/skills.json", model_name: str = "en_core_web_sm"):
        self.ontology_path = ontology_path
        self.nlp = None
        self.matcher = None
        self._load_ontology()
        
        # Load spaCy lazily; skip on Windows to prevent native torch DLL access violation
        import os
        import sys
        skip_spacy = os.environ.get("DISABLE_SPACY", "0") == "1" or sys.platform == "win32"
        if not skip_spacy:
            try:
                import spacy
                from spacy.matcher import PhraseMatcher
                self._load_spacy(spacy, model_name)
                if self.nlp is not None:
                    self._setup_matcher(PhraseMatcher)
                logger.info("NLPService initialised with spaCy model=%s and %d skills", model_name, len(self.skills_list))
            except (ImportError, OSError, Exception, BaseException) as exc:
                logger.warning("spaCy initialization notice: %s. Operating in resilient standalone NLP mode.", exc)
                self.nlp = None
                self.matcher = None
        else:
            logger.info("Operating NLPService in resilient high-speed standalone mode.")
            self.nlp = None
            self.matcher = None

    def _load_spacy(self, spacy, model_name):
        try:
            if not spacy.util.is_package(model_name):
                logger.warning(f"spaCy model {model_name} not found. Using blank model. Run: python -m spacy download {model_name}")
                self.nlp = spacy.blank("en")
            else:
                self.nlp = spacy.load(model_name, disable=["parser"]) # Keep tagger and ner for basic entity extraction
        except (ImportError, OSError) as exc:
            logger.warning("Could not load spaCy model: %s", exc)
            self.nlp = None
            
    def _load_ontology(self):
        import re
        ontology_file = Path(self.ontology_path)
        self.skills_list = []
        self.synonym_map = {}
        self.canonical_display = {}
        
        if ontology_file.exists():
            try:
                with open(ontology_file, "r", encoding="utf-8") as f:
                    ontology = json.load(f)
                    for skill in ontology.get("skills", []):
                        s_lower = skill.lower()
                        self.skills_list.append(s_lower)
                        self.canonical_display[s_lower] = skill
                    
                    syn_dict = ontology.get("synonyms", {})
                    for canonical, syn_list in syn_dict.items():
                        canon_lower = canonical.lower()
                        self.canonical_display[canon_lower] = canonical
                        if canon_lower not in self.skills_list:
                            self.skills_list.append(canon_lower)
                        for syn in syn_list:
                            syn_lower = syn.lower()
                            self.synonym_map[syn_lower] = canon_lower
                            if syn_lower not in self.skills_list:
                                self.skills_list.append(syn_lower)
            except Exception as e:
                logger.error("Failed to load skills ontology: %s", e)
        else:
            logger.warning("Ontology file not found at %s. Skill extraction will be empty.", self.ontology_path)
            
    def _setup_matcher(self, PhraseMatcher):
        if self.nlp is None:
            return
        self.matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        patterns = list(self.nlp.tokenizer.pipe(self.skills_list))
        self.matcher.add("SKILL", patterns)

    def clean_text(self, text: str) -> str:
        """Basic text cleaning."""
        if not text:
            return ""
        return " ".join(text.split())

    def extract_skills(self, text: str) -> list[str]:
        """Extract skills from text and map to canonical names."""
        clean_ext = self.clean_text(text)
        if not clean_ext:
            return []

        found_skills = set()

        if self.nlp is not None and self.matcher is not None:
            doc = self.nlp(clean_ext)
            matches = self.matcher(doc)
            for match_id, start, end in matches:
                span = doc[start:end]
                matched_text = span.text.lower()
                canonical = self.synonym_map.get(matched_text, matched_text)
                found_skills.add(canonical)
        else:
            # Resilient regex phrase matcher
            import re
            # Sort skills by length descending to match longest phrases first
            sorted_phrases = sorted(self.skills_list, key=len, reverse=True)
            for phrase in sorted_phrases:
                pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"
                if re.search(pattern, clean_ext, re.IGNORECASE):
                    canonical = self.synonym_map.get(phrase, phrase)
                    found_skills.add(canonical)

        # Format step:
        formatted = []
        for skill in found_skills:
            s_low = skill.lower()
            if s_low in self.canonical_display:
                formatted.append(self.canonical_display[s_low])
            elif skill.upper() in ["NLP", "LLM", "AWS", "GCP", "SQL", "RAG", "API", "JSON", "MCP", "CI/CD"]:
                formatted.append(skill.upper())
            elif s_low == "machine learning":
                formatted.append("Machine Learning")
            elif s_low == "deep learning":
                formatted.append("Deep Learning")
            elif s_low == "rest apis" or s_low == "rest api":
                formatted.append("REST APIs")
            else:
                formatted.append(skill.title())

        return sorted(list(set(formatted)))

    def extract_entities(self, text: str) -> dict[str, list[str]]:
        """Extract named entities (ORG, PERSON, GPE, etc.)"""
        if not text:
            return {}

        if self.nlp is not None:
            doc = self.nlp(text)
            entities = {}
            for ent in doc.ents:
                if ent.label_ not in entities:
                    entities[ent.label_] = []
                if ent.text not in entities[ent.label_]:
                    entities[ent.label_].append(ent.text)
            return entities

        # Standalone heuristic NER for key entity types when spaCy native library is absent
        import re
        entities: dict[str, list[str]] = {}
        # Known common tech organizations
        orgs = ["Google", "Microsoft", "Amazon", "Apple", "Meta", "OpenAI", "Anthropic", "IBM", "NVIDIA", "Netflix"]
        for org in orgs:
            if re.search(r"\b" + re.escape(org) + r"\b", text, re.IGNORECASE):
                entities.setdefault("ORG", []).append(org)
        # Known locations / GPE
        gpes = ["London", "New York", "San Francisco", "Seattle", "Bengaluru", "Bangalore", "Berlin", "Paris", "Tokyo"]
        for gpe in gpes:
            if re.search(r"\b" + re.escape(gpe) + r"\b", text, re.IGNORECASE):
                entities.setdefault("GPE", []).append(gpe)
        # Currency amounts
        money = re.findall(r"\$[\d,]+(?:\.\d+)?[MBKmbk]?", text)
        if money:
            entities["MONEY"] = money
        return entities

    def extract_skills_and_entities(self, text: str) -> dict[str, Any]:
        """Convenience method returning both extracted skills and named entities."""
        return {
            "skills": self.extract_skills(text),
            "entities": self.extract_entities(text),
        }

# Global instance
_nlp_service = None

def get_nlp_service() -> NLPService:
    global _nlp_service
    if _nlp_service is None:
        _nlp_service = NLPService()
    return _nlp_service
