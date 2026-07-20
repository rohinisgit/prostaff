# employees/id_utils.py
"""
Branch-prefixed ID generation for Enrollment ID and Employee ID.

Enrollment ID prefixes (per branch code, see core.context_processors.branch_context
branch_order = ['B01','B02','B03','B04'] => Chennai, Thindivanam, Kancheepuram, Madurai):
    B01 (Chennai)       -> TRB01
    B02 (Thindivanam)   -> TRB02
    B03 (Kancheepuram)  -> TRB03
    B04 (Madurai)       -> TRB04

Employee ID prefixes:
    B01 (Chennai)       -> SPSB01
    B02 (Thindivanam)   -> SPSB02
    B03 (Kancheepuram)  -> SPSB03
    B04 (Madurai)       -> SPSB04

Full stored value = PREFIX + zero-padded running sequence, e.g. TRB010001.
In the edit UI, HR/Admin/Manager only ever touch the numeric suffix — the
prefix is derived from the employee's branch and shown/locked separately.
"""

ENROLLMENT_ID_PREFIXES = {
    'B01': 'TRB01',
    'B02': 'TRB02',
    'B03': 'TRB03',
    'B04': 'TRB04',
}

EMPLOYEE_ID_PREFIXES = {
    'B01': 'SPSB01',
    'B02': 'SPSB02',
    'B03': 'SPSB03',
    'B04': 'SPSB04',
}

SEQ_WIDTH = 4  # e.g. TRB010001


def enrollment_prefix_for_branch(branch):
    if not branch:
        return 'TRB00'
    return ENROLLMENT_ID_PREFIXES.get(branch.code, 'TRB00')


def employee_id_prefix_for_branch(branch):
    if not branch:
        return 'SPSB00'
    return EMPLOYEE_ID_PREFIXES.get(branch.code, 'SPSB00')


def _next_sequence(queryset_values, prefix):
    """queryset_values: an iterable of existing ID strings for this field."""
    max_seq = 0
    for val in queryset_values:
        if not val or not val.startswith(prefix):
            continue
        suffix = val[len(prefix):]
        if suffix.isdigit():
            max_seq = max(max_seq, int(suffix))
    return max_seq + 1


def generate_enrollment_id(branch):
    from employees.models import EmployeeProfile
    prefix = enrollment_prefix_for_branch(branch)
    existing = EmployeeProfile.objects.exclude(enrollment_id__isnull=True).exclude(
        enrollment_id__exact=''
    ).values_list('enrollment_id', flat=True)
    seq = _next_sequence(existing, prefix)
    return f"{prefix}{seq:0{SEQ_WIDTH}d}"


def generate_employee_id(branch):
    from core.models import User
    prefix = employee_id_prefix_for_branch(branch)
    existing = User.objects.exclude(employee_id__isnull=True).exclude(
        employee_id__exact=''
    ).values_list('employee_id', flat=True)
    seq = _next_sequence(existing, prefix)
    return f"{prefix}{seq:0{SEQ_WIDTH}d}"


def split_id(full_id, prefix):
    """Returns just the numeric suffix of a full ID, for editing in the UI."""
    if full_id and full_id.startswith(prefix):
        return full_id[len(prefix):]
    return ''