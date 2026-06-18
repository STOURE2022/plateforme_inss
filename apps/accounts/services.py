import pyotp
from .models import User


def generate_mfa_secret() -> str:
    """Generate a new TOTP secret for a user."""
    return pyotp.random_base32()


def verify_mfa_code(user: User, code: str) -> bool:
    """Verify a TOTP code for the given user."""
    if not user.mfa_secret:
        return False
    totp = pyotp.TOTP(user.mfa_secret)
    return totp.verify(code, valid_window=1)


def get_mfa_provisioning_uri(user: User) -> str:
    """Return the OTP Auth URI for QR-based enrollment."""
    totp = pyotp.TOTP(user.mfa_secret)
    return totp.provisioning_uri(name=user.email, issuer_name="e-INSS")


def enable_mfa(user: User, code: str) -> bool:
    """Enable MFA after verifying the initial code."""
    if verify_mfa_code(user, code):
        user.mfa_enabled = True
        user.save(update_fields=["mfa_enabled"])
        return True
    return False
