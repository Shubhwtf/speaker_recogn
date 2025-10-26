"""
Gemini AI Service for transcript analysis
"""
import google.generativeai as genai
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Configure Gemini key
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def analyze_transcript(transcript_text, utterances=None):
    """
    Analyze transcript using Gemini 2.5 Flash
    Returns: dict with summary, key_points, sentiment, and action_items
    """
    if not GEMINI_API_KEY:
        raise ValueError("Gemini API key not configured")
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')        
        prompt = f"""Analyze the following transcript and provide:
1. A concise summary (2-3 sentences)
2. 3-5 key points or main topics discussed
3. Overall sentiment (positive, neutral, negative, or mixed)
4. Any action items or next steps mentioned (if applicable)

Transcript:
{transcript_text}
"""
        if utterances and len(utterances) > 0:
            prompt += f"\n\nNote: This conversation involves {len(set([u.get('speaker', '') for u in utterances]))} different speakers."
        prompt += "\n\nProvide your analysis in a clear, structured format."
        response = model.generate_content(prompt)
        
        if not response or not response.text:
            raise ValueError("Empty response from Gemini")
        analysis_text = response.text        
        result = {
            'summary': extract_section(analysis_text, 'summary'),
            'key_points': extract_list(analysis_text, 'key points', 'key point'),
            'sentiment': extract_sentiment(analysis_text),
            'action_items': extract_list(analysis_text, 'action items', 'action item', 'next steps'),
            'raw_analysis': analysis_text
        }
        
        logger.info(f"Successfully analyzed transcript with Gemini")
        return result
        
    except Exception as e:
        logger.error(f"Gemini analysis error: {e}")
        raise

def extract_section(text, section_name):
    """Extract a specific section from the analysis"""
    try:
        text_lower = text.lower()
        section_lower = section_name.lower()
        
        if section_lower in text_lower:
            start_idx = text_lower.index(section_lower)
            remaining_text = text[start_idx:]
            lines = remaining_text.split('\n')
            
            result_lines = []
            for line in lines[1:]:
                line = line.strip()
                if line and not line[0].isdigit() and ':' not in line[:20]:
                    result_lines.append(line)
                    if len(result_lines) >= 3:
                        break
                elif line and result_lines:
                    break
            
            if result_lines:
                return ' '.join(result_lines)
        
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        return paragraphs[0] if paragraphs else "Analysis not available"
    except:
        return "Analysis not available"

def extract_list(text, *section_names):
    """Extract a list of items from a section"""
    try:
        text_lower = text.lower()
        
        for section_name in section_names:
            section_lower = section_name.lower()
            if section_lower in text_lower:
                start_idx = text_lower.index(section_lower)
                remaining_text = text[start_idx:]
                lines = remaining_text.split('\n')
                
                items = []
                for line in lines[1:]:
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith('-') or line.startswith('*') or line.startswith('•')):
                        cleaned = line.lstrip('0123456789.-*•) ').strip()
                        if cleaned:
                            items.append(cleaned)
                    elif items and not line:
                        break                
                if items:
                    return items[:5]
        
        return []
    except:
        return []

def extract_sentiment(text):
    """Extract sentiment from analysis"""
    try:
        text_lower = text.lower()
        
        if 'sentiment' in text_lower:
            start_idx = text_lower.index('sentiment')
            snippet = text_lower[start_idx:start_idx + 100]
            
            for sentiment in ['positive', 'negative', 'neutral', 'mixed']:
                if sentiment in snippet:
                    return sentiment.capitalize()
        
        positive_words = ['positive', 'good', 'great', 'excellent', 'happy', 'pleased']
        negative_words = ['negative', 'bad', 'poor', 'unhappy', 'concerned', 'worried']
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return "Positive"
        elif negative_count > positive_count:
            return "Negative"
        elif positive_count == negative_count and positive_count > 0:
            return "Mixed"
        
        return "Neutral"
    except:
        return "Neutral"

def generate_meeting_summary(transcript_text, utterances, duration_seconds):
    """
    Generate a comprehensive meeting summary
    """
    if not GEMINI_API_KEY:
        raise ValueError("Gemini API key not configured")
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        speakers = list(set([u.get('speaker', '') for u in utterances])) if utterances else []
        
        prompt = f"""Generate a professional meeting summary for the following transcript:

Duration: {duration_seconds // 60} minutes
Participants: {len(speakers)} speakers

Transcript:
{transcript_text}

Please provide:
1. Executive Summary (2-3 sentences)
2. Main Discussion Points (3-5 points)
3. Decisions Made
4. Action Items with responsible parties (if identifiable)
5. Key Takeaways

Format the summary professionally and concisely."""
        
        response = model.generate_content(prompt)
        
        return {
            'summary': response.text if response and response.text else "Summary not available",
            'generated_at': 'timestamp'
        }
        
    except Exception as e:
        logger.error(f"Meeting summary generation error: {e}")
        raise

