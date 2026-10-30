"""
Search Tools.

Provides structured tools for researching companies, job listings, and market data.
Implements Pydantic validation, safe timeouts, and graceful fallbacks for offline testing.
"""

from __future__ import annotations

import logging
from typing import List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class CompanySearchInput(BaseModel):
    company_name: str = Field(..., description="Name of the company to research")
    industry: Optional[str] = Field("Artificial Intelligence", description="Industry or focus area")


class CompanyProfile(BaseModel):
    name: str
    industry: str
    description: str
    headquarters: str
    founded: str
    key_technologies: List[str]
    culture_highlights: List[str]
    source_url: str
    verified: bool = True


class JobSearchInput(BaseModel):
    query: str = Field(..., description="Job role query, e.g. 'AI Engineer' or 'Machine Learning'")
    location: Optional[str] = Field("Remote", description="Location or remote preference")
    limit: int = Field(5, ge=1, le=20, description="Maximum number of listings to return")


class JobSummary(BaseModel):
    job_id: str
    title: str
    company: str
    location: str
    experience_level: str
    key_requirements: List[str]
    source_url: str


class JobSearchOutput(BaseModel):
    total_found: int
    jobs: List[JobSummary]


class JobDetailsInput(BaseModel):
    job_id: str = Field(..., description="Unique identifier for the job posting")


class JobDetails(BaseModel):
    job_id: str
    title: str
    company: str
    location: str
    description: str
    required_skills: List[str]
    preferred_skills: List[str]
    responsibilities: List[str]
    source_url: str


# ── Curated Knowledge Repositories (Graceful Mock Fallback) ───────────────────

_COMPANIES_DB = {
    "deeptech labs": CompanyProfile(
        name="DeepTech Labs",
        industry="Enterprise Artificial Intelligence & Agentic Systems",
        description="A high-growth AI research and engineering company developing autonomous multi-agent decision support systems for Fortune 500 enterprises.",
        headquarters="San Francisco, CA (with global remote teams)",
        founded="2021",
        key_technologies=["Python", "LangGraph", "FastAPI", "FAISS", "Docker", "PyTorch", "Transformers"],
        culture_highlights=["Engineering-first culture", "Emphasis on grounded generative AI", "Open-source contributor"],
        source_url="https://deeptechlabs.ai/about",
    ),
    "quantum ai": CompanyProfile(
        name="Quantum AI Technologies",
        industry="Next-Generation Generative AI Platforms",
        description="Pioneering enterprise AI workflows integrating large language models with real-world deterministic execution engines and human-in-the-loop governance.",
        headquarters="New York, NY",
        founded="2022",
        key_technologies=["Python", "LangGraph", "ChromaDB", "FastAPI", "Kubernetes", "Hugging Face"],
        culture_highlights=["Rapid iteration", "Rigorous AI evaluation", "Safety and guardrails"],
        source_url="https://quantumai.tech/company",
    ),
    "google": CompanyProfile(
        name="Google",
        industry="Technology, Search & Artificial Intelligence",
        description="Global leader in search, cloud computing, and advanced AI research through Google DeepMind.",
        headquarters="Mountain View, CA",
        founded="1998",
        key_technologies=["TensorFlow", "JAX", "Gemini", "Kubernetes", "Python", "C++"],
        culture_highlights=["Research excellence", "Scale and reliability", "Innovation"],
        source_url="https://about.google",
    ),
    "microsoft": CompanyProfile(
        name="Microsoft",
        industry="Cloud, Productivity & Enterprise AI",
        description="Multinational technology corporation powering enterprise transformation with Azure AI and Copilot ecosystems.",
        headquarters="Redmond, WA",
        founded="1975",
        key_technologies=["Azure OpenAI", "Python", "Semantic Kernel", "C#", "Docker"],
        culture_highlights=["Enterprise grade security", "Global scale", "Customer trust"],
        source_url="https://microsoft.com/about",
    ),
    "ibm": CompanyProfile(
        name="IBM (International Business Machines)",
        industry="Enterprise Cloud, Cognitive AI & Hybrid Computing",
        description="Global enterprise technology leader pioneering Watsonx AI, Red Hat OpenShift hybrid cloud architectures, quantum computing, and mission-critical enterprise systems.",
        headquarters="Armonk, NY (Global labs in Bengaluru, Hyderabad, San Jose)",
        founded="1911",
        key_technologies=["Python", "Java", "watsonx", "Red Hat OpenShift", "Kubernetes", "SQL", "Cloud Pak", "Docker"],
        culture_highlights=["Client dedication", "Trust & personal responsibility", "Continuous innovation & cognitive certifications"],
        source_url="https://www.ibm.com/about",
    ),
    "infosys": CompanyProfile(
        name="Infosys",
        industry="Next-Generation Digital Services & Consulting",
        description="Global leader in next-generation digital transformation, AI-first platforms (Infosys Topaz), cloud suites (Infosys Cobalt), and enterprise core modernization across 56+ countries.",
        headquarters="Bengaluru, Karnataka, India",
        founded="1981",
        key_technologies=["Java", "Python", "Infosys Topaz (AI)", "Cloud (AWS/Azure/GCP)", "Spring Boot", "SQL", "Microservices", "React"],
        culture_highlights=["Global delivery model", "World-class Mysore training campus", "HackWithInfy innovation challenges"],
        source_url="https://www.infosys.com/about",
    ),
    "tcs": CompanyProfile(
        name="Tata Consultancy Services (TCS)",
        industry="IT Services, Digital Transformation & AI Solutions",
        description="Flagship IT powerhouse of the Tata Group, driving large-scale digital architectures, enterprise AI, cloud migration, and fintech platforms worldwide.",
        headquarters="Mumbai, Maharashtra, India",
        founded="1968",
        key_technologies=["Python", "Java", "C++", "SQL", "Azure", "AWS", "Big Data", "Machine Learning"],
        culture_highlights=["Values-driven culture", "TCS CodeVita global hackathon", "Long-term career growth"],
        source_url="https://www.tcs.com/about-us",
    ),
    "amazon": CompanyProfile(
        name="Amazon",
        industry="Cloud Computing (AWS), E-Commerce & Artificial Intelligence",
        description="Pioneer in cloud computing with Amazon Web Services (AWS), Bedrock GenAI platforms, large-scale recommendation systems, and autonomous robotics.",
        headquarters="Seattle, WA",
        founded="1994",
        key_technologies=["Java", "Python", "AWS", "DynamoDB", "Distributed Systems", "SageMaker", "PyTorch"],
        culture_highlights=["Customer Obsession", "Ownership", "Bias for Action", "High Hiring Bar"],
        source_url="https://aboutamazon.com",
    ),
    "accenture": CompanyProfile(
        name="Accenture",
        industry="Global Professional Services, Technology & AI",
        description="Global professional services company with leading capabilities in digital, cloud, security, and generative AI enterprise adoption.",
        headquarters="Dublin, Ireland (Global Centers in India, US, Europe)",
        founded="1989",
        key_technologies=["Cloud Architecture", "Python", "Java", "GenAI", "Salesforce", "SAP", "Data Analytics"],
        culture_highlights=["High-velocity client delivery", "Continuous upskilling", "Inclusion & Diversity"],
        source_url="https://www.accenture.com/about",
    ),
    "nvidia": CompanyProfile(
        name="NVIDIA",
        industry="Accelerated Computing, GPU Architecture & AI Foundations",
        description="Pioneer in GPU-accelerated computing, CUDA architecture, DGX SuperPODs, and enterprise foundational AI models.",
        headquarters="Santa Clara, CA (India Centers: Bengaluru, Pune)",
        founded="1993",
        key_technologies=["CUDA", "PyTorch", "TensorRT", "C++", "Python", "Deep Learning", "Docker"],
        culture_highlights=["Deep technical craftsmanship", "First-principles engineering", "High autonomy"],
        source_url="https://www.nvidia.com/about",
    ),
    "adobe": CompanyProfile(
        name="Adobe",
        industry="Digital Media, Generative AI (Firefly) & Cloud Systems",
        description="Global leader in digital creativity, document infrastructure, and creative generative AI technologies.",
        headquarters="San Jose, CA (India Hubs: Noida, Bengaluru)",
        founded="1982",
        key_technologies=["Python", "C++", "Computer Vision", "Machine Learning", "FastAPI", "React"],
        culture_highlights=["Genuine employee wellness", "Creativity for all", "High retention and patent bonuses"],
        source_url="https://www.adobe.com/about-adobe",
    ),
    "zoho": CompanyProfile(
        name="Zoho Corporation",
        industry="SaaS, Enterprise Cloud Applications & Private AI",
        description="Bootstrapped global SaaS leader running 55+ business applications on self-hosted datacenters and rural technology campuses.",
        headquarters="Chennai, Tamil Nadu, India",
        founded="1996",
        key_technologies=["Java", "Python", "Cloud Infrastructure", "Linux", "Distributed Systems", "SQL"],
        culture_highlights=["Zero external debt / bootstrapping", "Rural technology campuses", "Focus on core engineering"],
        source_url="https://www.zoho.com/aboutus.html",
    ),
    "flipkart": CompanyProfile(
        name="Flipkart (Walmart Group)",
        industry="E-Commerce, Logistics & Large-Scale Recommendation Systems",
        description="India's leading consumer e-commerce ecosystem powering high-scale distributed commerce architectures and supply chain AI.",
        headquarters="Bengaluru, Karnataka, India",
        founded="2007",
        key_technologies=["Java", "Python", "Distributed Systems", "Machine Learning", "Kafka", "SQL"],
        culture_highlights=["Audacity and customer-first mindset", "High-scale engineering problems", "Meritocracy"],
        source_url="https://about.flipkart.com",
    ),
    "uber": CompanyProfile(
        name="Uber",
        industry="Global Mobility, Autonomous Systems & Marketplace AI",
        description="Global mobility and logistics platform operating real-time dispatch, dynamic pricing, and marketplace balancing engines at massive scale.",
        headquarters="San Francisco, CA (Tech Centers: Bengaluru, Hyderabad)",
        founded="2009",
        key_technologies=["Go", "Java", "Python", "Machine Learning", "Kafka", "Distributed Systems"],
        culture_highlights=["Build with purpose", "Go get it mindset", "Exceptional engineering bar"],
        source_url="https://www.uber.com/about",
    ),
    "meta": CompanyProfile(
        name="Meta",
        industry="Frontier Open AI (Llama), Social Platforms & PyTorch",
        description="Global technology leader developing the open-weight Llama AI foundation models, PyTorch core, and next-generation connectivity.",
        headquarters="Menlo Park, CA (Tech Hubs: Bengaluru, Hyderabad)",
        founded="2004",
        key_technologies=["PyTorch", "Python", "C++", "Distributed Systems", "LLMs", "Transformers"],
        culture_highlights=["Move fast", "Open source leadership", "World-class compensation"],
        source_url="https://about.meta.com",
    ),
    "target technology partner": CompanyProfile(
        name="Target Technology Partner",
        industry="Enterprise Artificial Intelligence & Cloud Modernization",
        description="Premier technology enterprise hiring for high-performance software engineering, cloud data platforms, and applied generative AI.",
        headquarters="Metropolitan Technology Corridor",
        founded="2015",
        key_technologies=["Python", "Machine Learning", "FastAPI", "SQL", "Docker", "Cloud Architecture"],
        culture_highlights=["Continuous engineering growth", "High-impact delivery", "Collaborative culture"],
        source_url="https://enterprise-ai-platform.internal/partner",
    ),
}

_JOBS_DB = {
    "job-ai-001": JobDetails(
        job_id="job-ai-001",
        title="AI/ML Engineer - Multi-Agent Platforms",
        company="DeepTech Labs",
        location="Remote (Global)",
        description="We are seeking an AI/ML Engineer to build state-of-the-art multi-agent decision support platforms using LangGraph, RAG pipelines, and modern NLP.",
        required_skills=["Python", "LangGraph", "RAG", "Vector Databases", "FastAPI", "Machine Learning", "Docker"],
        preferred_skills=["Evaluation Frameworks", "Human-in-the-Loop Systems", "PyTorch", "Sentence Transformers"],
        responsibilities=[
            "Design and orchestrate multi-agent architectures using LangGraph",
            "Develop robust RAG pipelines with dense vector search (FAISS/Chroma)",
            "Build production-grade FastAPI microservices and Docker containers",
            "Implement automated evaluation, toxicity guardrails, and HITL approval gates",
        ],
        source_url="https://deeptechlabs.ai/careers/job-ai-001",
    ),
    "job-genai-002": JobDetails(
        job_id="job-genai-002",
        title="Generative AI & Agentic Systems Engineer",
        company="Quantum AI Technologies",
        location="Remote (US / Europe / India)",
        description="Join our core platform team building enterprise-grade generative AI workflows, tool calling agents, and decision-support systems.",
        required_skills=["Python", "LLMs", "LangGraph", "Embeddings", "NLP", "FastAPI", "SQL"],
        preferred_skills=["Scikit-learn", "CI/CD", "Docker", "Prompt Engineering"],
        responsibilities=[
            "Architect agentic workflows with LangGraph StateGraph and MemorySaver",
            "Engineer semantic search and hybrid document retrieval pipelines",
            "Collaborate with product and safety teams to enforce human-in-the-loop governance",
        ],
        source_url="https://quantumai.tech/jobs/job-genai-002",
    ),
    "job-ibm-003": JobDetails(
        job_id="job-ibm-003",
        title="Associate Software Engineer / Cognitive Developer",
        company="IBM",
        location="Bengaluru / Hyderabad / Pune / Hybrid",
        description="Join IBM Client Engineering to engineer scalable cloud-native microservices, Watsonx enterprise AI solutions, and hybrid cloud backends.",
        required_skills=["Python", "Java", "Data Structures & Algorithms", "SQL", "Cloud Fundamentals", "Git"],
        preferred_skills=["Red Hat OpenShift", "Docker", "Machine Learning Basics", "REST APIs"],
        responsibilities=[
            "Develop and maintain microservices in Python / Java",
            "Work with IBM Cloud Pak and Red Hat OpenShift container platforms",
            "Solve algorithmic and computational problems with clean, modular code",
            "Collaborate across global agile development sprints",
        ],
        source_url="https://www.ibm.com/careers",
    ),
    "job-infy-004": JobDetails(
        job_id="job-infy-004",
        title="Specialist Programmer (Digital Specialist Engineer)",
        company="Infosys",
        location="Bengaluru / Mysore / Hyderabad / Pune",
        description="Elite engineering track at Infosys focused on building cutting-edge full-stack architectures, high-performance distributed systems, and Topaz AI platforms.",
        required_skills=["Java", "Python", "Data Structures & Algorithms", "OOP Concepts", "SQL", "Problem Solving"],
        preferred_skills=["Spring Boot", "React", "Cloud Basics (AWS/Azure)", "Docker"],
        responsibilities=[
            "Architect and implement high-throughput enterprise systems",
            "Pass rigorous competitive coding assessments and technical deep dives",
            "Deploy microservices to modern containerized cloud infrastructures",
            "Contribute to AI-first automation solutions under Infosys Topaz",
        ],
        source_url="https://www.infosys.com/careers",
    ),
}


# ── Tool Functions ────────────────────────────────────────────────────────────

def search_company(input_data: CompanySearchInput) -> CompanyProfile:
    """
    Search for structured company intelligence.
    Returns verified company profile or graceful synthesized profile if not in catalog.
    """
    logger.info("Executing search_company tool for '%s'", input_data.company_name)
    key = input_data.company_name.strip().lower()

    # Exact or substring match in curated database
    for db_key, profile in _COMPANIES_DB.items():
        if db_key in key or key in db_key:
            return profile

    # Graceful fallback for arbitrary company names
    return CompanyProfile(
        name=input_data.company_name.title(),
        industry=input_data.industry or "Technology & AI Services",
        description=f"A modern enterprise operating in {input_data.industry or 'AI'}, adopting modern intelligent workflow platforms.",
        headquarters="Metropolitan Technology Hub",
        founded="2020",
        key_technologies=["Python", "Machine Learning", "FastAPI", "Cloud Infrastructure"],
        culture_highlights=["Innovation", "Data-driven decision making", "Agile delivery"],
        source_url=f"https://www.{key.replace(' ', '')}.com/about",
        verified=False,
    )


def search_jobs(input_data: JobSearchInput) -> JobSearchOutput:
    """
    Search active job opportunities matching keywords.
    """
    logger.info("Executing search_jobs tool for query='%s'", input_data.query)
    q = input_data.query.lower()
    matches: List[JobSummary] = []

    for job in _JOBS_DB.values():
        if any(term in job.title.lower() or term in job.description.lower() for term in q.split()):
            matches.append(
                JobSummary(
                    job_id=job.job_id,
                    title=job.title,
                    company=job.company,
                    location=job.location,
                    experience_level="Mid to Senior / High Potential Intern",
                    key_requirements=job.required_skills,
                    source_url=job.source_url,
                )
            )

    # If no exact keyword match, return standard curated listings
    if not matches:
        for job in list(_JOBS_DB.values())[:input_data.limit]:
            matches.append(
                JobSummary(
                    job_id=job.job_id,
                    title=job.title,
                    company=job.company,
                    location=job.location,
                    experience_level="Mid / Graduate",
                    key_requirements=job.required_skills,
                    source_url=job.source_url,
                )
            )

    return JobSearchOutput(total_found=len(matches), jobs=matches[:input_data.limit])


def get_job_details(input_data: JobDetailsInput) -> JobDetails:
    """
    Retrieve full details for a specified job listing ID.
    """
    logger.info("Executing get_job_details tool for job_id='%s'", input_data.job_id)
    if input_data.job_id in _JOBS_DB:
        return _JOBS_DB[input_data.job_id]

    # Return default benchmark listing if ID not found
    return _JOBS_DB["job-ai-001"]
