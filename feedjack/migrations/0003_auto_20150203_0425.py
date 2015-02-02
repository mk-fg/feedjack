# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feedjack', '0002_auto_20150203_0401'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feed',
            name='verify_tls_certs',
            field=models.BooleanField(default=True, help_text='If https connections are used, this option allows to disable TLS certificate veritication. Has no effect with python versions before 2.7.9, where TLS certs are never checked.', verbose_name='verify TLS certificates, if any'),
            preserve_default=True,
        ),
    ]
