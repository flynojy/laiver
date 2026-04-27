FACT_AUTO_COMMIT_MIN_IMPORTANCE = 0.75
FACT_AUTO_COMMIT_MIN_CONFIDENCE = 0.72
REVIEW_REQUIRED_SENSITIVITY = {"sensitive", "private", "high"}

DECAY_POLICY_RATES = {
    "session": 0.08,
    "volatile": 0.05,
    "default": 0.02,
    "slow": 0.01,
    "stable": 0.005,
    "permanent": 0.0,
}

DECAY_POLICY_GRACE_DAYS = {
    "session": 0,
    "volatile": 3,
    "default": 14,
    "slow": 30,
    "stable": 90,
    "permanent": 36500,
}

FACT_ARCHIVE_STABILITY_THRESHOLD = 0.12
FACT_ARCHIVE_IMPORTANCE_THRESHOLD = 0.2
STALE_CANDIDATE_DAYS = 30
