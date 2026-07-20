from django.db import migrations

BRANCHES = [
    ('Chennai', 'B01'),
    ('Thindivanam', 'B02'),
    ('Kancheepuram', 'B03'),
    ('Madurai', 'B04'),
]


def seed_branches(apps, schema_editor):
    Branch = apps.get_model('core', 'Branch')
    User = apps.get_model('core', 'User')

    for name, code in BRANCHES:
        Branch.objects.get_or_create(code=code, defaults={'name': name})

    # Everything that already existed in the system belongs to Chennai —
    # nothing changes for current data, Chennai just becomes explicit.
    chennai = Branch.objects.get(code='B01')
    User.objects.filter(branch__isnull=True).update(branch=chennai)


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
       ('core', '0004_user_can_access_all_branches_branch_user_branch'),
    ]

    operations = [
        migrations.RunPython(seed_branches, reverse_noop),
    ]