from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Interview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('resume_file', models.FileField(upload_to='resumes/')),
                ('resume_text', models.TextField(blank=True, default='')),
                ('questions', models.TextField(blank=True, default='[]')),
                ('answers', models.TextField(blank=True, default='[]')),
                ('evaluation', models.TextField(blank=True, default='{}')),
                ('status', models.CharField(choices=[('uploaded', 'Resume Uploaded'), ('analyzing', 'Analyzing Resume'), ('ready', 'Ready for Interview'), ('in_progress', 'Interview In Progress'), ('evaluating', 'Evaluating Answers'), ('completed', 'Interview Completed')], default='uploaded', max_length=20)),
                ('share_token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('share_clicks', models.PositiveIntegerField(default=0)),
                ('share_visits', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
