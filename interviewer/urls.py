"""
URL configuration for the interviewer app.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Page routes
    path('', views.index, name='index'),
    path('upload/', views.upload, name='upload'),
    path('interview/<int:interview_id>/', views.interview_page, name='interview_page'),
    path('result/<int:interview_id>/', views.result_page, name='result_page'),
    path('share/<uuid:share_token>/', views.shared_result_page, name='shared_result_page'),

    # API endpoints for AJAX calls
    path('api/ask/', views.api_ask, name='api_ask'),
    path('api/evaluate/', views.api_evaluate, name='api_evaluate'),
    path('api/share-event/', views.api_share_event, name='api_share_event'),
]
