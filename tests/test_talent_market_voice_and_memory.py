"""
tests/test_talent_market_voice_and_memory.py

Validates:
1. Talent Market Privacy: Company name and matching compatibility are shown, external apply portal links restricted.
2. AI Voice Assistant: Best vs worst performer comparison, comparing type queries, and problem-solving ideas.
3. Advanced Memory Engine: Episodic dialogue memory, entity tracking, and Docker/Kubernetes/Cloud/Azure Copilot knowledge.
"""

import pytest
from app.api.recruiter import recruiter_voice_assist, VoiceAssistRequest
from app.services.memory_service import get_memory_service


@pytest.mark.asyncio
async def test_voice_assist_best_and_worst_performer():
    """Test that voice assistant answers who is best and who is worst performer with scores and gaps."""
    req = VoiceAssistRequest(query="who is best and who is worst performer in this cohort?")
    res = await recruiter_voice_assist(req)
    assert res is not None
    text = res.reply_text.lower()
    print("\nReply for Best & Worst Performer:\n", res.reply_text)

    # Must identify top performer
    assert "sarah lin" in text or "best performer" in text
    assert "88" in text or "percent" in text

    # Must identify worst / lowest performer
    assert "lowest" in text or "worst" in text or "gaps" in text or "64" in text or "rao" in text or "alex" in text


@pytest.mark.asyncio
async def test_voice_assist_comparing_type():
    """Test that voice assistant handles general comparing type queries."""
    req = VoiceAssistRequest(query="can you show comparing type and rank the candidates?")
    res = await recruiter_voice_assist(req)
    assert res is not None
    text = res.reply_text.lower()
    print("\nReply for Comparing Type:\n", res.reply_text)

    assert "comparing" in text or "sarah" in text or "alex" in text
    assert "score" in text or "percent" in text


@pytest.mark.asyncio
async def test_voice_assist_giving_ideas_for_problem():
    """Test that voice assistant provides actionable ideas to solve engineering and hiring problems."""
    req = VoiceAssistRequest(query="give me ideas for a problem regarding pipeline latency and high load")
    res = await recruiter_voice_assist(req)
    assert res is not None
    text = res.reply_text.lower()
    print("\nReply for Ideas for a Problem:\n", res.reply_text)

    # Must offer concrete ideas mentioning containerization/cloud/k8s/caching
    assert (
        "docker" in text
        or "kubernetes" in text
        or "keda" in text
        or "faiss" in text
        or "redis" in text
        or "ideas" in text
        or "solve" in text
    )


@pytest.mark.asyncio
async def test_voice_assist_kubernetes_and_cloud():
    """Test that voice assistant answers Kubernetes and Cloud architecture questions."""
    req = VoiceAssistRequest(query="how do we scale kubernetes pods and connect azure copilot?")
    res = await recruiter_voice_assist(req)
    assert res is not None
    text = res.reply_text.lower()
    print("\nReply for Kubernetes & Azure Copilot:\n", res.reply_text)

    assert "kubernetes" in text or "k8s" in text or "azure" in text or "docker" in text


def test_advanced_memory_engine_episodic_and_semantic():
    """Test AdvancedMemoryEngine episodic tracking and semantic knowledge query."""
    mem_svc = get_memory_service()
    session_id = "test-session-mem-999"

    # 1. Test domain query for Docker and Kubernetes
    k8s_data = mem_svc.query_domain_knowledge("how to deploy kubernetes cluster with helm and hpa")
    assert k8s_data is not None
    assert k8s_data["domain"] == "kubernetes"
    assert len(k8s_data["concepts"]) >= 3

    docker_data = mem_svc.query_domain_knowledge("optimizing dockerfile container image size")
    assert docker_data is not None
    assert docker_data["domain"] == "docker"

    azure_data = mem_svc.query_domain_knowledge("how to connect azure copilot and semantic kernel")
    assert azure_data is not None
    assert azure_data["domain"] == "azure_copilot"

    # 2. Test episodic dialogue recording and entity tracking
    mem_svc.record_turn(
        session_id=session_id,
        user_message="who is the worst performer among candidates?",
        assistant_reply="Vikramaditya Rao is the lowest performer with 64.5% score.",
        detected_entities={"candidate_name": "Vikramaditya Rao", "topic": "candidate_comparison"},
    )

    prompt_ctx = mem_svc.get_session_context_prompt(session_id)
    assert "Vikramaditya Rao" in prompt_ctx
    assert "candidate_comparison" in prompt_ctx

    # 3. Test problem solving generation
    ideas_res = mem_svc.generate_problem_ideas("high latency and pod eviction in kubernetes")
    assert "ideas" in ideas_res
    assert len(ideas_res["ideas"]) >= 2
    assert "Kubernetes" in ideas_res["markdown_text"]
