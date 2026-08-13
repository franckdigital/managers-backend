from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('progression', '0003_courseprogressionsettings_attendance_signature_required_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('courses', '0001_initial'),
    ]

    operations = [
        # Nouveaux champs sur LessonProgress
        migrations.AddField(
            model_name='lessonprogress',
            name='open_count',
            field=models.PositiveIntegerField(default=0, help_text='Nombre de fois que la leçon a été ouverte'),
        ),
        migrations.AddField(
            model_name='lessonprogress',
            name='video_play_count',
            field=models.PositiveIntegerField(default=0, help_text='Nombre de fois que la vidéo a été lancée'),
        ),
        migrations.AddField(
            model_name='lessonprogress',
            name='last_opened_at',
            field=models.DateTimeField(blank=True, help_text='Dernière ouverture de la leçon', null=True),
        ),
        # Nouveau modèle CourseView
        migrations.CreateModel(
            name='CourseView',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('open_count', models.PositiveIntegerField(default=1, help_text="Nombre de fois que la page cours a été ouverte")),
                ('last_opened_at', models.DateTimeField(auto_now=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_views', to='courses.course')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='course_views', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'course')},
            },
        ),
    ]
