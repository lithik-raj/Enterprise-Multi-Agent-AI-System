"""
tests/test_voice_assist_employee.py
Tests AI Voice Assistant handling employee management, routine work, and role suitability questions.
"""
import pytest
from app.api.recruiter import recruiter_voice_assist, VoiceAssistRequest

@pytest.mark.asyncio
async def test_voice_assist_who_is_divya_balaji():
    req = VoiceAssistRequest(query="who is divya balaji in our compnay?")
    res = await recruiter_voice_assist(req)
    assert res is not None
    text = res.reply_text.lower()
    print("\nReply for Who is Divya Balaji:", res.reply_text)
    assert "divya balaji" in text
    assert "human resources" in text or "talent" in text or "emp-1013" in text
    assert res.candidate_name == "Divya Balaji"


@pytest.mark.asyncio
async def test_voice_assist_what_works_doing():
    # Follow-up pronoun test with candidate_name preserved
    req = VoiceAssistRequest(query="what works he is doing ?", candidate_name="Divya Balaji")
    res = await recruiter_voice_assist(req)
    assert res is not None
    text = res.reply_text.lower()
    print("\nReply for What works is she doing:", res.reply_text)
    assert "divya balaji" in text
    assert "routine work" in text or "onboarding" in text or "documentation" in text


@pytest.mark.asyncio
async def test_voice_assist_is_she_suitable_data_scientist():
    req = VoiceAssistRequest(query="is he suitable for the data scieintist", candidate_name="Divya Balaji")
    res = await recruiter_voice_assist(req)
    assert res is not None
    text = res.reply_text.lower()
    print("\nReply for Is Divya suitable for data scientist:", res.reply_text)
    assert "divya balaji" in text
    assert "data scientist" in text
    assert "compatibility score" in text or "percent" in text
    # Divya is HR, so suitability should identify gaps or recommend training
    assert "upskilling" in text or "prerequisites" in text or "lacks" in text or "gaps" in text or "percent" in text


@pytest.mark.asyncio
async def test_voice_assist_suitable_vikram_malhotra():
    req = VoiceAssistRequest(query="is vikram malhotra suitable for the data scientist")
    res = await recruiter_voice_assist(req)
    assert res is not None
    text = res.reply_text.lower()
    print("\nReply for Is Vikram suitable for data scientist:", res.reply_text)
    assert "vikram malhotra" in text
    assert "suitable" in text
    assert "percent" in text


@pytest.mark.asyncio
async def test_voice_assist_how_many_employees():
    req = VoiceAssistRequest(query="how many employees in our company?")
    res = await recruiter_voice_assist(req)
    assert res is not None
    text = res.reply_text.lower()
    print("\nReply for How many employees:", res.reply_text)
    assert "employees" in text or "20" in text or "staff" in text
