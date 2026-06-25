# Maps each tool to the set of valid preceding tools.
# None means the tool can be called at any time (entry point or standalone).
# Tools not in this dict are standalone — they don't affect flow state.

FLOW_RULES: dict[str, list[str] | None] = {
    # Aadhaar enrollment
    "aadhaar_enrollment_init": None,
    "aadhaar_enrollment_verify_otp": ["aadhaar_enrollment_init"],
    "aadhaar_enrollment_verify_mobile_otp": ["aadhaar_enrollment_verify_otp"],
    "aadhaar_enrollment_suggest_address": [
        "aadhaar_enrollment_verify_otp",
        "aadhaar_enrollment_verify_mobile_otp",
    ],
    "aadhaar_enrollment_create_address": ["aadhaar_enrollment_suggest_address"],

    # Biometric enrollment — standalone, no predecessor
    "enroll_abha_by_biometric": None,

    # ABHA verification
    "verify_abha_init": None,
    "verify_abha_confirm": ["verify_abha_init", "verify_abha_confirm"],

    # ABHA address verification
    "search_abha_address_auth_methods": None,
    "abha_address_verification_init": ["search_abha_address_auth_methods"],
    "abha_address_verification_confirm": ["abha_address_verification_init"],

    # Find ABHA
    "search_abha": None,
    "find_abha_init": ["search_abha"],
    "find_abha_verify": ["find_abha_init"],
}

# Tools not in FLOW_RULES are standalone — always allowed, don't update flow state.
# e.g. get_abha_profile, get_abha_qr, get_abha_card, get_session, invalidate_session

SESSION_TTL = 600  # 10 minutes
