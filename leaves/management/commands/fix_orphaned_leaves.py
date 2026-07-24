from django.core.management.base import BaseCommand
from leaves.models import LeaveRequest


class Command(BaseCommand):
    help = (
        "Finds LeaveRequest rows stuck as PENDING_MANAGER whose stored "
        "manager no longer resolves correctly (e.g. the request was "
        "submitted before a manager existed for that branch/department). "
        "For each one, re-checks get_manager() against current data: if a "
        "valid manager now exists, the request is left as-is (it should "
        "already be visible to that manager); if none exists, the request "
        "is moved to PENDING_HR so it isn't stuck forever."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help="Actually save changes. Without this flag, the command only reports what it WOULD do.",
        )

    def handle(self, *args, **options):
        apply_changes = options['apply']
        stuck = LeaveRequest.objects.filter(status='PENDING_MANAGER').select_related('user', 'user__branch', 'user__department')

        if not stuck.exists():
            self.stdout.write(self.style.SUCCESS("No PENDING_MANAGER requests found. Nothing to check."))
            return

        fixed = 0
        ok = 0

        for lr in stuck:
            manager = lr.get_manager()

            if manager is not None:
                ok += 1
                self.stdout.write(
                    f"[OK]      #{lr.id} {lr.user} -> resolves to manager {manager} "
                    f"(branch: {manager.branch}). Should already show in their dashboard."
                )
                continue

            fixed += 1
            self.stdout.write(
                self.style.WARNING(
                    f"[ORPHAN]  #{lr.id} {lr.user} (branch: {lr.user.branch}) -> no valid manager found. "
                    f"{'Moving to PENDING_HR.' if apply_changes else 'Would move to PENDING_HR (dry run).'}"
                )
            )
            if apply_changes:
                lr.status = 'PENDING_HR'
                lr.save()

        self.stdout.write("")
        if apply_changes:
            self.stdout.write(self.style.SUCCESS(f"Done. {fixed} request(s) moved to PENDING_HR, {ok} already fine."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dry run complete. {fixed} request(s) would be moved to PENDING_HR, {ok} already fine.\n"
                    f"Re-run with --apply to actually save changes."
                )
            )