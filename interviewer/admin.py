"""
Admin configuration for the interviewer app.
"""
from django.contrib import admin
from .models import Interview


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'created_at', 'updated_at')
    list_filter = ('status',)
    readonly_fields = ('created_at', 'updated_at')
