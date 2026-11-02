import uuid
import django.db.models.deletion
from django.db import migrations, models


def acessos_individuais(apps, schema_editor):
    Sessao = apps.get_model('restaurante', 'SessaoMesa')
    for sessao in Sessao.objects.using(schema_editor.connection.alias).all().iterator():
        sessao.acesso_uuid = uuid.uuid4()
        sessao.save(using=schema_editor.connection.alias, update_fields=['acesso_uuid'])


class Migration(migrations.Migration):
    dependencies = [('restaurante', '0007_historicostatuspedido_motivo_and_more')]
    operations = [
        migrations.RemoveConstraint(model_name='sessaomesa', name='uma_sessao_ativa_por_mesa'),
        migrations.AddField(model_name='sessaomesa', name='acesso_uuid',
            field=models.UUIDField(null=True, editable=False)),
        migrations.RunPython(acessos_individuais, migrations.RunPython.noop),
        migrations.AlterField(model_name='sessaomesa', name='acesso_uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
        migrations.CreateModel(name='ConviteComanda', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
            ('expira_em', models.DateTimeField()),
            ('sessao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='convites', to='restaurante.sessaomesa')),
        ]),
    ]
