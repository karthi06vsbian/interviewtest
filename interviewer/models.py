"""
Models for the AI Interview application.
Stores interview sessions with resume data, questions, answers, and results.
"""
import json
import uuid
from django.db import models


class Interview(models.Model):
    """Represents a single interview session."""

    # Status choices for the interview lifecycle
    STATUS_CHOICES = [
        ('uploaded', 'Resume Uploaded'),
        ('analyzing', 'Analyzing Resume'),
        ('ready', 'Ready for Interview'),
        ('in_progress', 'Interview In Progress'),
        ('evaluating', 'Evaluating Answers'),
        ('completed', 'Interview Completed'),
    ]

    # Resume data
    resume_file = models.FileField(upload_to='resumes/')
    resume_text = models.TextField(blank=True, default='')

    # Interview data stored as JSON strings
    questions = models.TextField(blank=True, default='[]')   # JSON list of questions
    answers = models.TextField(blank=True, default='[]')     # JSON list of answers

    # Evaluation results stored as JSON
    evaluation = models.TextField(blank=True, default='{}')

    # Interview metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    share_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    share_clicks = models.PositiveIntegerField(default=0)
    share_visits = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_questions(self):
        """Return questions as a Python list."""
        try:
            return json.loads(self.questions)
        except json.JSONDecodeError:
            return []

    def set_questions(self, questions_list):
        """Save a Python list as JSON string."""
        self.questions = json.dumps(questions_list)

    def get_answers(self):
        """Return answers as a Python list."""
        try:
            return json.loads(self.answers)
        except json.JSONDecodeError:
            return []

    def set_answers(self, answers_list):
        """Save a Python list as JSON string."""
        self.answers = json.dumps(answers_list)

    def get_evaluation(self):
        """Return evaluation as a Python dict."""
        try:
            return json.loads(self.evaluation)
        except json.JSONDecodeError:
            return {}

    def set_evaluation(self, eval_dict):
        """Save a Python dict as JSON string."""
        self.evaluation = json.dumps(eval_dict)

    def ensure_share_token(self):
        """Ensure a share token exists for link generation."""
        if not self.share_token:
            self.share_token = uuid.uuid4()

    def __str__(self):
        return f"Interview #{self.id} — {self.status} — {self.created_at:%Y-%m-%d %H:%M}"
