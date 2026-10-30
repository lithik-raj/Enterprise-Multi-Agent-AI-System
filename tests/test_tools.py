"""
Phase 7 — Tools tests.
Run with:   pytest tests/test_tools.py -v
"""

import json
from unittest.mock import patch, MagicMock
from app.tools.rag_tools import retrieve_context_tool
from app.tools.analysis_tools import extract_skills_tool, calculate_compatibility_tool


def test_retrieve_context_tool_found():
    with patch("app.tools.rag_tools.get_rag_retriever") as mock_get:
        mock_retriever = MagicMock()
        mock_retriever.search_context.return_value = ["Context A", "Context B"]
        mock_get.return_value = mock_retriever
        
        result = retrieve_context_tool(query="test", document_ids=["1"])
        assert "--- Excerpt 1 ---" in result
        assert "Context A" in result
        assert "Context B" in result


def test_retrieve_context_tool_not_found():
    with patch("app.tools.rag_tools.get_rag_retriever") as mock_get:
        mock_retriever = MagicMock()
        mock_retriever.search_context.return_value = []
        mock_get.return_value = mock_retriever
        
        result = retrieve_context_tool(query="test")
        assert result == "No relevant context found in documents."


def test_extract_skills_tool():
    with patch("app.tools.analysis_tools.get_nlp_service") as mock_nlp:
        mock_service = MagicMock()
        mock_service.extract_skills.return_value = ["Python", "AWS"]
        mock_nlp.return_value = mock_service
        
        result_json = extract_skills_tool("I know Python and AWS.")
        result = json.loads(result_json)
        assert result["extracted_skills"] == ["Python", "AWS"]


def test_calculate_compatibility_tool_with_skills_provided():
    with patch("app.tools.analysis_tools.get_ml_service") as mock_ml:
        mock_service = MagicMock()
        mock_service.calculate_text_similarity.return_value = 0.8
        mock_service.calculate_skill_overlap.return_value = {
            "overlap_score": 0.5,
            "missing_skills": ["AWS"],
            "matched_skills": ["Python"]
        }
        mock_service.calculate_overall_compatibility.return_value = 0.62
        mock_ml.return_value = mock_service
        
        res_json = calculate_compatibility_tool(
            resume_text="...",
            job_text="...",
            required_skills=["Python", "AWS"],
            present_skills=["Python", "GCP"]
        )
        
        res_dict = json.loads(res_json)
        assert res_dict["semantic_similarity"] == 0.8
        assert res_dict["overall_compatibility_score"] == 0.62
        assert res_dict["missing_skills"] == ["AWS"]
