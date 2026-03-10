def guide_button_id(level: str) -> str:
    return {
        "Lower Risk": "guide_lower_risk",
        "Caution": "guide_caution",
        "Extreme Caution": "guide_extreme_caution",
        "Danger": "guide_danger",
        "Extreme Danger": "guide_extreme_danger",
    }[level]