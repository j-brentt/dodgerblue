# Generated manually: add liked_by relation to comments

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entries', '0008_comment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='liked_by',
            field=models.ManyToManyField(blank=True, related_name='liked_comments', to=settings.AUTH_USER_MODEL),
        ),
    ]
