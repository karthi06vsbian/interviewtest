from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Interview


class ShareResultFeatureTests(TestCase):
    def setUp(self):
        self.resume_file = SimpleUploadedFile(
            'resume.pdf',
            b'%PDF-1.4 test resume content',
            content_type='application/pdf',
        )
        self.interview = Interview.objects.create(
            resume_file=self.resume_file,
            resume_text='Test resume',
            status='completed',
        )
        self.interview.set_evaluation({
            'score': 8.7,
            'communication': 8,
            'technical': 9,
            'confidence': 8,
            'clarity': 9,
            'summary': 'Strong interview performance.',
            'strengths': ['Clear examples'],
            'weaknesses': ['Could add more detail'],
            'suggestions': ['Practice concise storytelling'],
        })
        self.interview.save()

    def tearDown(self):
        if self.interview.resume_file:
            self.interview.resume_file.delete(save=False)

    def test_result_page_includes_share_link(self):
        response = self.client.get(reverse('result_page', args=[self.interview.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Copy Share Link')
        self.assertContains(response, reverse('shared_result_page', args=[self.interview.share_token]))

    def test_share_event_increments_share_clicks(self):
        response = self.client.post(
            reverse('api_share_event'),
            data='{"interview_id": %d, "event": "share_clicked"}' % self.interview.id,
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.interview.refresh_from_db()
        self.assertEqual(self.interview.share_clicks, 1)

    def test_shared_result_page_increments_share_visits_and_shows_cta(self):
        response = self.client.get(
            reverse('shared_result_page', args=[self.interview.share_token])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Start Your Interview')
        self.interview.refresh_from_db()
        self.assertEqual(self.interview.share_visits, 1)
