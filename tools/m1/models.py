from typing import Optional
from pydantic import BaseModel, Field


# ── Aadhaar Enrollment ──────────────────────────────────────────────────────

class AadhaarEnrollmentInitInput(BaseModel):
    aadhaar_number: str = Field(..., description="12-digit Aadhaar number of the patient")


class AadhaarEnrollmentVerifyOTPInput(BaseModel):
    txn_id: str = Field(..., description="Transaction ID returned from aadhaar_enrollment_init")
    otp: str = Field(..., description="OTP received on the Aadhaar-linked mobile number")
    mobile: str = Field(..., description="10-digit mobile number of the patient")


class AadhaarEnrollmentVerifyMobileOTPInput(BaseModel):
    txn_id: str = Field(..., description="Transaction ID from the previous enrollment step")
    otp: str = Field(..., description="OTP received on the patient's mobile number")


class UserDetailInput(BaseModel):
    first_name: str = Field(default="", description="Patient's first name")
    last_name: str = Field(default="", description="Patient's last name")
    day_of_birth: str = Field(default="", description="Day of birth (DD)")
    month_of_birth: str = Field(default="", description="Month of birth (MM)")
    year_of_birth: str = Field(default="", description="Year of birth (YYYY)")


class AadhaarEnrollmentSuggestAddressInput(BaseModel):
    txn_id: str = Field(..., description="Transaction ID from the previous enrollment step")
    user_detail: UserDetailInput = Field(
        default_factory=UserDetailInput,
        description="Patient name and date of birth for generating ABHA address suggestions"
    )


class AadhaarEnrollmentCreateAddressInput(BaseModel):
    txn_id: str = Field(..., description="Transaction ID from the previous enrollment step")
    abha_address: str = Field(
        ..., description="Chosen ABHA address from the suggestions list (without @abdm suffix)"
    )


class EnrollABHAByBiometricInput(BaseModel):
    aadhaar_number: str = Field(..., description="12-digit Aadhaar number of the patient")
    pid: str = Field(..., description="Biometric PID block captured from the biometric device")
    mobile_number: str = Field(..., description="10-digit mobile number of the patient")


# ── ABHA Verification ───────────────────────────────────────────────────────

class VerifyABHAInitInput(BaseModel):
    method: str = Field(
        ...,
        description=(
            "Verification method. One of: "
            "'aadhaar_otp' (Aadhaar number, OTP via UIDAI), "
            "'abha_number_aadhaar_otp' (ABHA number, OTP via UIDAI), "
            "'abha_number_abha_otp' (ABHA number, OTP via ABDM), "
            "'mobile_otp' (mobile number, OTP via ABDM)"
        )
    )
    identifier: str = Field(
        ...,
        description=(
            "The identifier matching the chosen method: "
            "12-digit Aadhaar for aadhaar_otp, "
            "ABHA number (91-xxxx-xxxx-xxxx) for abha_number_* methods, "
            "10-digit mobile for mobile_otp"
        )
    )


class VerifyABHAConfirmInput(BaseModel):
    txn_id: str = Field(..., description="Transaction ID returned from verify_abha_init")
    otp: Optional[str] = Field(
        default=None,
        description="OTP received by the patient. Provide for the OTP verification step."
    )
    abha_number: Optional[str] = Field(
        default=None,
        description=(
            "ABHA number to select when multiple accounts are returned (skip_state=abha_select). "
            "Leave empty for the OTP step."
        )
    )


# ── ABHA Address Verification ───────────────────────────────────────────────

class SearchABHAAddressAuthMethodsInput(BaseModel):
    abha_address: str = Field(..., description="ABHA address to look up (e.g. patient@abdm)")


class ABHAAddressVerificationInitInput(BaseModel):
    abha_address: str = Field(..., description="ABHA address to verify (e.g. patient@abdm)")
    method: str = Field(
        ..., description="Auth method to use for verification. One of: 'mobile', 'aadhaar'"
    )


class ABHAAddressVerificationConfirmInput(BaseModel):
    txn_id: str = Field(
        ..., description="Transaction ID returned from abha_address_verification_init"
    )
    otp: str = Field(
        ..., description="OTP received by the patient on their registered mobile/Aadhaar"
    )


# ── Find ABHA ───────────────────────────────────────────────────────────────

class SearchABHAInput(BaseModel):
    mobile: str = Field(..., description="10-digit mobile number to search ABHA profiles by")


class FindABHAInitInput(BaseModel):
    txn_id: str = Field(..., description="Transaction ID returned from search_abha")
    index: str = Field(
        ..., description="Index of the ABHA profile selected from the search_abha results"
    )
    otp_system: str = Field(
        ..., description="OTP delivery system. One of: 'abdm', 'aadhaar'"
    )


class FindABHAVerifyInput(BaseModel):
    txn_id: str = Field(..., description="Transaction ID from find_abha_init")
    otp: str = Field(..., description="OTP received by the patient")


class GetABHAProfileInput(BaseModel):
    abha_address: str = Field(..., description="ABHA address of the patient (e.g. patient@abdm)")


class GetABHAQRInput(BaseModel):
    abha_address: str = Field(..., description="ABHA address of the patient to fetch QR code for")


class GetABHACardInput(BaseModel):
    abha_address: str = Field(..., description="ABHA address of the patient to fetch ABHA card for")


class SessionInput(BaseModel):
    abha_address: str = Field(..., description="ABHA address of the patient (e.g. patient@abdm)")
