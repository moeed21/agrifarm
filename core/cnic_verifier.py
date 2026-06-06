"""
AgriBazaar — cnic_verifier.py
Manual review mode: saves photos, marks status as 'pending' for admin approval.
"""


def verify(cnic_front_field, cnic_back_field) -> str:
    """
    Manual review — always returns 'pending'.
    Admin approves or rejects from the admin panel.
    """
    return 'pending'
