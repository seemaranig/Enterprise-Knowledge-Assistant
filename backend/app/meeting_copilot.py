"""
PHASE 7: Meeting Copilot Features

Purpose: Analyze meeting transcripts for:
- Automatic meeting summaries
- Action item extraction
- Risk identification
- Decision extraction
- Attendee tracking

Use Cases:
1. Upload meeting transcript (text file)
2. Get structured analysis
3. Track decisions and actions across meetings
4. Risk mitigation planning
"""

from typing import List, Dict, Any
import json
from datetime import datetime

from langchain_community.llms import Ollama

from app.config import get_settings
from app.logger import logger
from app.exceptions import LLMError


def analyze_meeting_transcript(
    transcript: str,
    meeting_title: str,
    attendees: List[str] = None
) -> Dict[str, Any]:
    """
    Analyze meeting transcript using specialized agents.
    
    Args:
        transcript: Meeting transcript text
        meeting_title: Title of the meeting
        attendees: List of attendees
        
    Returns:
        Dict with summary, actions, risks, decisions
    """
    
    settings = get_settings()
    llm = Ollama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.3  # Lower temp for structured extraction
    )
    
    try:
        # Extract summaries, actions, risks, decisions
        logger.info(f"Analyzing meeting: {meeting_title}")
        
        # Generate summary
        summary_prompt = f"""Summarize this meeting in 2-3 sentences:

{transcript}

Summary:"""
        summary = llm.invoke(summary_prompt).strip()
        
        # Extract action items
        actions_prompt = f"""Extract all action items from this transcript. Format as JSON array:

{transcript}

[{{"assignee": "name", "action": "description", "deadline": "if mentioned"}}]"""
        
        try:
            actions_text = llm.invoke(actions_prompt)
            actions = json.loads(actions_text)
        except:
            actions = []
        
        # Extract risks
        risks_prompt = f"""What risks or concerns were discussed? List them:

{transcript}

Risks:"""
        risks_text = llm.invoke(risks_prompt).strip()
        
        # Extract decisions
        decisions_prompt = f"""What decisions were made? List them:

{transcript}

Decisions:"""
        decisions_text = llm.invoke(decisions_prompt).strip()
        
        result = {
            "meeting_title": meeting_title,
            "summary": summary,
            "action_items": actions,
            "risks": risks_text.split('\n'),
            "decisions": decisions_text.split('\n'),
            "attendees": attendees or [],
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Meeting analysis complete: {len(actions)} actions, {len(risks_text.split(chr(10)))} risks")
        return result
        
    except Exception as e:
        logger.error(f"Meeting analysis failed: {str(e)}")
        raise LLMError(f"Failed to analyze meeting: {str(e)}")
