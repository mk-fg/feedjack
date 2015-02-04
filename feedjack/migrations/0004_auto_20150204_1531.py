# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feedjack', '0003_auto_20150203_0425'),
    ]

    operations = [
        migrations.AlterField(
            model_name='filterbase',
            name='crossref',
            field=models.BooleanField(default=False, help_text=b'Indicates whether filtering results depend on other posts (and possibly their filtering results) or not.<br /> Note that ordering in which these filters are applied to a posts, as well as "update condition" should match for any cross-referenced feeds. This restriction might go away in the future.', verbose_name=b'Cross-referencing'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='filterresult',
            name='result',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
