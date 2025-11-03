# Generated manually: add Comment model for entry discussion

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('entries', '0007_remove_entry_likes_entry_liked_by'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to=settings.AUTH_USER_MODEL)),
                ('entry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='entries.entry')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
    ]
