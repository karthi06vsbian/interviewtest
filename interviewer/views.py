"""
Views for the AI Interview application.
Handles page rendering and API endpoints for the interview flow.
"""
import json
from django.db.models import F
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Interview
from .utils import (
    parse_pdf,
    analyze_resume,
    get_interviewer_response,
    evaluate_interview,
    GENERAL_QUESTIONS,
)


# ─── Page Views ──────────────────────────────────────────────────────

def index(request):
    """Landing page with welcome message and Start Interview button."""
    return render(request, 'interviewer/index.html')


def upload(request):
    """
    GET:  Show the resume upload form.
    POST: Process the uploaded PDF, analyze the resume, and redirect to interview.
    """
    if request.method == 'POST':
        # Validate that a file was uploaded
        if 'resume' not in request.FILES:
            return render(request, 'interviewer/upload.html', {
                'error': 'Please select a PDF file to upload.'
            })

        resume_file = request.FILES['resume']

        # Validate file type
        if not resume_file.name.lower().endswith('.pdf'):
            return render(request, 'interviewer/upload.html', {
                'error': 'Only PDF files are accepted. Please upload a PDF resume.'
            })

        # Validate file size (max 5MB)
        if resume_file.size > 5 * 1024 * 1024:
            return render(request, 'interviewer/upload.html', {
                'error': 'File too large. Please upload a PDF smaller than 5MB.'
            })

        try:
            # Parse PDF text
            resume_text = parse_pdf(resume_file)

            # Create interview record
            interview = Interview(
                resume_file=resume_file,
                resume_text=resume_text,
                status='analyzing',
            )
            interview.save()

            # Analyze resume and generate questions
            resume_questions = analyze_resume(resume_text)

            # Combine resume questions with general questions (10 total)
            all_questions = resume_questions[:5] + GENERAL_QUESTIONS[:5]
            interview.set_questions(all_questions)
            interview.status = 'ready'
            interview.save()

            return redirect('interview_page', interview_id=interview.id)

        except ValueError as e:
            return render(request, 'interviewer/upload.html', {
                'error': str(e)
            })
        except Exception as e:
            return render(request, 'interviewer/upload.html', {
                'error': f'An unexpected error occurred: {str(e)}'
            })

    return render(request, 'interviewer/upload.html')


def interview_page(request, interview_id):
    """Render the interview chat interface."""
    interview = get_object_or_404(Interview, id=interview_id)
    questions = interview.get_questions()

    return render(request, 'interviewer/interview.html', {
        'interview': interview,
        'questions_json': json.dumps(questions),
        'total_questions': len(questions),
    })


def result_page(request, interview_id):
    """Render the evaluation results page."""
    interview = get_object_or_404(Interview, id=interview_id)
    interview.ensure_share_token()
    if interview.pk:
        interview.save(update_fields=['share_token'])
    evaluation = interview.get_evaluation()
    share_url = request.build_absolute_uri(
        reverse('shared_result_page', args=[interview.share_token])
    )

    return render(request, 'interviewer/result.html', {
        'interview': interview,
        'evaluation': evaluation,
        'share_url': share_url,
        'share_metrics': {
            'share_clicked': interview.share_clicks,
            'shared_result_opened': interview.share_visits,
        },
        'is_public_share': False,
    })


def shared_result_page(request, share_token):
    """Render a public, shareable version of the interview result."""
    interview = get_object_or_404(Interview, share_token=share_token, status='completed')
    Interview.objects.filter(id=interview.id).update(share_visits=F('share_visits') + 1)
    interview.refresh_from_db(fields=['share_visits'])
    evaluation = interview.get_evaluation()

    return render(request, 'interviewer/result.html', {
        'interview': interview,
        'evaluation': evaluation,
        'share_url': request.build_absolute_uri(),
        'share_metrics': {
            'share_clicked': interview.share_clicks,
            'shared_result_opened': interview.share_visits,
        },
        'is_public_share': True,
    })


# ─── API Endpoints ───────────────────────────────────────────────────

@csrf_exempt
@require_POST
def api_ask(request):
    """
    API endpoint: Get AI interviewer's response to a user's answer.
    Expects JSON body: { interview_id, question, answer, question_number, total_questions }
    Returns JSON: { response }
    """
    try:
        data = json.loads(request.body)
        interview_id = data.get('interview_id')
        question = data.get('question', '')
        answer = data.get('answer', '')
        question_number = data.get('question_number', 1)
        total_questions = data.get('total_questions', 10)

        # Get AI response
        ai_response = get_interviewer_response(
            question, answer, question_number, total_questions
        )

        # Save the answer to the interview
        interview = Interview.objects.get(id=interview_id)
        answers = interview.get_answers()
        answers.append(answer)
        interview.set_answers(answers)
        interview.status = 'in_progress'
        interview.save()

        return JsonResponse({'response': ai_response})

    except Interview.DoesNotExist:
        return JsonResponse({'error': 'Interview not found.'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def api_evaluate(request):
    """
    API endpoint: Evaluate all interview answers.
    Expects JSON body: { interview_id, questions, answers }
    Returns JSON: evaluation results
    """
    try:
        data = json.loads(request.body)
        interview_id = data.get('interview_id')
        questions = data.get('questions', [])
        answers = data.get('answers', [])

        # Run evaluation
        evaluation = evaluate_interview(questions, answers)

        # Save evaluation to the interview record
        interview = Interview.objects.get(id=interview_id)
        interview.set_answers(answers)
        interview.set_evaluation(evaluation)
        interview.status = 'completed'
        interview.save()

        return JsonResponse({'evaluation': evaluation})

    except Interview.DoesNotExist:
        return JsonResponse({'error': 'Interview not found.'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def api_share_event(request):
    """
    API endpoint: Track share-related events on completed interviews.
    Expects JSON body: { interview_id, event }
    Returns JSON: { ok, share_clicks, share_visits }
    """
    try:
        data = json.loads(request.body)
        interview_id = data.get('interview_id')
        event = data.get('event')

        if event != 'share_clicked':
            return JsonResponse({'error': 'Unsupported event.'}, status=400)

        interview = Interview.objects.get(id=interview_id, status='completed')
        Interview.objects.filter(id=interview.id).update(share_clicks=F('share_clicks') + 1)
        interview.refresh_from_db(fields=['share_clicks', 'share_visits'])

        return JsonResponse({
            'ok': True,
            'share_clicks': interview.share_clicks,
            'share_visits': interview.share_visits,
        })

    except Interview.DoesNotExist:
        return JsonResponse({'error': 'Interview not found.'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
