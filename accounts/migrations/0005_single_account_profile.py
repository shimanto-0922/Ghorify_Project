"""One account for everyone: tenant/landlord roles become 'user', and the two
profile tables are merged into a single Profile (verification data is kept)."""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models



def roles_to_user(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(role__in=['tenant', 'landlord']).update(role='user')


def merge_tenant_documents(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    Profile = apps.get_model('accounts', 'Profile')
    TenantProfile = apps.get_model('accounts', 'TenantProfile')
    for tp in TenantProfile.objects.all():
        profile, _ = Profile.objects.get_or_create(user_id=tp.user_id)
        if tp.nid_document and not profile.nid_document:
            profile.nid_document = tp.nid_document
        if tp.birth_certificate and not profile.birth_certificate:
            profile.birth_certificate = tp.birth_certificate
        if (tp.nid_document or tp.birth_certificate) and profile.status == 'unsubmitted':
            profile.status = 'pending'
        profile.save()
    # Every normal user gets a profile.
    for user in User.objects.exclude(role='admin').filter(profile__isnull=True):
        Profile.objects.create(user=user)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_remove_tenantprofile_family_size_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('user', 'User'), ('admin', 'Admin')], default='user', max_length=10),
        ),
        migrations.RunPython(roles_to_user, migrations.RunPython.noop),
        migrations.RenameModel('LandlordProfile', 'Profile'),
        migrations.RenameField('profile', 'verification_docs', 'nid_document'),
        migrations.AlterField(
            model_name='profile',
            name='nid_document',
            field=models.FileField(blank=True, null=True, upload_to='verification/', verbose_name='NID'),
        ),
        migrations.AddField(
            model_name='profile',
            name='birth_certificate',
            field=models.FileField(blank=True, null=True, upload_to='verification/'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='profile',
            name='verified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='verified_profiles', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(merge_tenant_documents, migrations.RunPython.noop),
        migrations.DeleteModel(name='TenantProfile'),
    ]
