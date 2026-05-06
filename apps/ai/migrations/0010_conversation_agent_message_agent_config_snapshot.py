import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0001_initial'),
        ('ai', '0009_message_responding_to'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='agent',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='conversations',
                to='agents.agent',
            ),
        ),
        migrations.AddField(
            model_name='message',
            name='agent_config_snapshot',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
