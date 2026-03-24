"""
Utility functions for PDF parsing and Groq AI integration.
Handles all AI-related operations: resume analysis, interview Q&A, evaluation.
"""
import json
import re
import pdfplumber
from django.conf import settings
from groq import Groq


# ─── PDF Parsing ─────────────────────────────────────────────────────

def parse_pdf(file_obj):
    """
    Extract text from an uploaded PDF file.
    Args:
        file_obj: Django UploadedFile or file-like object
    Returns:
        str: Extracted text from all pages
    """
    text = ""
    try:
        with pdfplumber.open(file_obj) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {str(e)}")

    if not text.strip():
        raise ValueError("No text could be extracted from the PDF. Please upload a valid resume.")

    return text.strip()


# ─── Groq API Client ────────────────────────────────────────────────

def get_groq_client():
    """Create and return a Groq API client."""
    api_key = settings.GROQ_API_KEY
    if not api_key or api_key == 'YOUR_GROQ_API_KEY_HERE':
        raise ValueError(
            "Groq API key is not configured. "
            "Please set GROQ_API_KEY in settings.py or as an environment variable."
        )
    return Groq(api_key=api_key)


def get_ai_response(system_prompt, user_message, temperature=0.7):
    """
    Send a chat completion request to the Groq API.
    Args:
        system_prompt: System-level instructions for the AI
        user_message: The user's message/prompt
        temperature: Creativity level (0.0 - 1.0)
    Returns:
        str: AI response text
    """
    client = get_groq_client()

    try:
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_completion_tokens=2048,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise ValueError(f"Groq API error: {str(e)}")


# ─── Resume Analysis ────────────────────────────────────────────────

def analyze_resume(resume_text):
    """
    Analyze resume text and generate personalized interview questions.
    Args:
        resume_text: Extracted text from the resume PDF
    Returns:
        list: List of 5 personalized interview questions
    """
    system_prompt = (
        "You are an expert resume analyst and HR professional. "
        "Analyze the given resume carefully and generate interview questions."
    )

    user_prompt = f"""Analyze this resume and extract:
- Skills
- Projects
- Education
- Experience

Then generate exactly 5 personalized interview questions based on it.

IMPORTANT: Return your response as a valid JSON object with this exact structure:
{{
    "skills": ["skill1", "skill2"],
    "projects": ["project1", "project2"],
    "education": ["education1"],
    "experience": ["experience1"],
    "questions": [
        "Question 1 based on resume?",
        "Question 2 based on resume?",
        "Question 3 based on resume?",
        "Question 4 based on resume?",
        "Question 5 based on resume?"
    ]
}}

Resume:
{resume_text}"""

    response = get_ai_response(system_prompt, user_prompt, temperature=0.5)

    # Try to parse the JSON from the response
    try:
        # Try to find JSON block in the response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            data = json.loads(json_match.group())
            return data.get('questions', [])
    except json.JSONDecodeError:
        pass

    # Fallback: extract questions line by line
    lines = response.strip().split('\n')
    questions = []
    for line in lines:
        line = line.strip()
        # Look for numbered questions
        cleaned = re.sub(r'^[\d]+[\.\)]\s*', '', line)
        if cleaned and '?' in cleaned and len(cleaned) > 15:
            questions.append(cleaned)
    
    return questions[:5] if questions else [
        "Tell me about yourself and your background.",
        "What are your key technical skills?",
        "Describe a project you're most proud of.",
        "What challenges have you faced in your career?",
        "Where do you see yourself in 5 years?",
    ]


# ─── General Interview Questions ────────────────────────────────────

GENERAL_QUESTIONS = [
    "Can you walk me through your problem-solving approach when you encounter a difficult technical challenge?",
    "Tell me about a time when you worked effectively in a team. What role did you play?",
    "How do you handle tight deadlines and pressure at work?",
    "What motivates you to do your best work, and how do you stay productive?",
    "Do you have any questions for me about the role or the company?",
]


# ─── Interview Q&A ──────────────────────────────────────────────────

def get_interviewer_response(question, user_answer, question_number, total_questions):
    """
    Get the AI interviewer's response to a user's answer.
    Args:
        question: The question that was asked
        user_answer: The user's response
        question_number: Current question number (1-based)
        total_questions: Total number of questions
    Returns:
        str: AI interviewer's brief comment + transition
    """
    system_prompt = """You are a professional female HR interviewer named Sarah.
Speak politely and confidently.
You are conducting a job interview.
Keep your responses brief (2-3 sentences max).
Acknowledge the candidate's answer briefly, then naturally transition.
Do NOT ask the next question — it will be provided separately."""

    user_prompt = f"""The candidate was asked: "{question}"
Their answer was: "{user_answer}"
This was question {question_number} of {total_questions}.

Give a brief, encouraging acknowledgment of their answer (2-3 sentences max)."""

    return get_ai_response(system_prompt, user_prompt, temperature=0.6)


# ─── Evaluation ──────────────────────────────────────────────────────

def evaluate_interview(questions, answers):
    """
    Evaluate the candidate's interview performance.
    Args:
        questions: List of questions that were asked
        answers: List of the candidate's answers
    Returns:
        dict: Evaluation with score, strengths, weaknesses, suggestions
    """
    # Build Q&A pairs for the prompt
    qa_pairs = ""
    for i, (q, a) in enumerate(zip(questions, answers), 1):
        qa_pairs += f"\nQ{i}: {q}\nA{i}: {a}\n"

    system_prompt = """You are an expert HR interviewer evaluator.
Evaluate interview performance fairly and constructively.
Always return your evaluation as valid JSON."""

    user_prompt = f"""Evaluate the following candidate's interview answers:

{qa_pairs}

Give feedback on:
- Communication skills
- Technical knowledge
- Confidence level
- Clarity of answers
- Any mistakes or areas of concern

IMPORTANT: Return your evaluation as a valid JSON object with this EXACT structure:
{{
    "score": 7,
    "summary": "Brief overall assessment paragraph",
    "strengths": [
        "Strength 1",
        "Strength 2",
        "Strength 3"
    ],
    "weaknesses": [
        "Weakness 1",
        "Weakness 2"
    ],
    "suggestions": [
        "Suggestion 1",
        "Suggestion 2",
        "Suggestion 3"
    ],
    "communication": 7,
    "technical": 7,
    "confidence": 7,
    "clarity": 7
}}

Score should be out of 10. Sub-scores (communication, technical, confidence, clarity) should also be out of 10."""

    response = get_ai_response(system_prompt, user_prompt, temperature=0.4)

    # Try to parse JSON
    try:
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass

    # Fallback evaluation
    return {
        "score": 6,
        "summary": response,
        "strengths": ["Completed the interview"],
        "weaknesses": ["Could not parse detailed evaluation"],
        "suggestions": ["Practice more mock interviews"],
        "communication": 6,
        "technical": 6,
        "confidence": 6,
        "clarity": 6,
    }
