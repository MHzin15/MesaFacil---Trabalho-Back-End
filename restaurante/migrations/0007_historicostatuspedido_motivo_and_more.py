from django.db import migrations, models



class Migration(migrations.Migration):
    dependencies = [('restaurante', '0006_loginratebucket')]
    operations = [
        migrations.AddField(model_name='historicostatuspedido', name='motivo',
            field=models.CharField(blank=True, default='', max_length=500)),
        migrations.AddField(model_name='sessaomesa', name='versao_conta',
            field=models.PositiveIntegerField(default=1, editable=False)),
    ]
