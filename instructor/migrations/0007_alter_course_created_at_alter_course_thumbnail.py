# Generated by Django 5.1.5 on 2025-02-02 06:38

import embed_video.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('instructor', '0006_course_category_objects_course_created_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='course',
            name='thumbnail',
            field=embed_video.fields.EmbedVideoField(),
        ),
    ]
