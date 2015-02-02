# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feedjack', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='feed',
            name='verify_tls_certs',
            field=models.BooleanField(default=True, help_text='If https connections are used, this option allows to disable TLS certificate veritication.', verbose_name='verify TLS certificates, if any'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='feed',
            name='skip_errors',
            field=models.BooleanField(default=False, help_text='Try to be as tolerant to the feed contents as possible during update.', verbose_name='skip non-critical errors'),
            preserve_default=True,
        ),
    ]
