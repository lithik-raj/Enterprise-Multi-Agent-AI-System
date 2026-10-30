"""
Multi-Agent Tools Package.
"""

from app.tools.search_tools import (
    search_company,
    search_jobs,
    get_job_details,
    CompanySearchInput,
    CompanyProfile,
    JobSearchInput,
    JobSummary,
    JobDetailsInput,
    JobDetails,
)
from app.tools.document_tools import (
    analyze_document,
    DocumentAnalysisInput,
    DocumentAnalysisOutput,
)
from app.tools.ml_tools import (
    calculate_similarity,
    run_ml_prediction,
    SimilarityInput,
    SimilarityOutput,
    MLPredictionInput,
    MLPredictionOutput,
)
from app.tools.analysis_tools import (
    extract_skills_tool,
    calculate_compatibility_tool,
    extract_skills,
    generate_report,
    SkillExtractionInput,
    SkillExtractionOutput,
    ReportInput,
    ReportOutput,
)
from app.tools.rag_tools import (
    retrieve_context_tool,
    retrieve_knowledge,
    KnowledgeRetrievalInput,
    KnowledgeRetrievalOutput,
)

__all__ = [
    "search_company",
    "search_jobs",
    "get_job_details",
    "CompanySearchInput",
    "CompanyProfile",
    "JobSearchInput",
    "JobSummary",
    "JobDetailsInput",
    "JobDetails",
    "analyze_document",
    "DocumentAnalysisInput",
    "DocumentAnalysisOutput",
    "calculate_similarity",
    "run_ml_prediction",
    "SimilarityInput",
    "SimilarityOutput",
    "MLPredictionInput",
    "MLPredictionOutput",
    "extract_skills_tool",
    "calculate_compatibility_tool",
    "extract_skills",
    "generate_report",
    "SkillExtractionInput",
    "SkillExtractionOutput",
    "ReportInput",
    "ReportOutput",
    "retrieve_context_tool",
    "retrieve_knowledge",
    "KnowledgeRetrievalInput",
    "KnowledgeRetrievalOutput",
]
