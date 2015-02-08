# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feedjack', '0014_add_postproc_base_example'),
    ]

    operations = [
        migrations.RenameField(
            model_name='postprocessorresult',
            old_name='_overlay',
            new_name='overlay_dump',
        ),
    ]
