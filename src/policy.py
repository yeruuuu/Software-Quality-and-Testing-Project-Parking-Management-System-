from decimal import Decimal

POLICY = {
    # Global
    "cutoff_time": "04:00",  # 4 AM daily cut-off
    "grace_minutes": 15,     # Default 15-minute grace for timed zones

    # Zones
    "zones": {
        "REGULAR": {
            "members_only": False,
            "grace_minutes": 15,
            "weekday": {"first2h_flat": Decimal("4.00"), "per_hour": Decimal("4.00")},
            "weekend": {"first2h_flat": Decimal("2.00"), "per_hour": Decimal("4.00")},
            "public_holiday": {"first2h_flat": Decimal("2.00"), "per_hour": Decimal("3.00")},
            "daily_cap": Decimal("20.00"),
            "overnight_penalty": Decimal("80.00"),
        },
        "PREFERRED": {
            "members_only": True,
            "grace_minutes": 15,
            "weekday": {"first2h_flat": Decimal("3.00"), "per_hour": Decimal("4.00")},
            "weekend": {"first2h_flat": Decimal("2.00"), "per_hour": Decimal("3.00")},
            "public_holiday": {"first2h_flat": Decimal("2.00"), "per_hour": Decimal("2.00")},
            "daily_cap": Decimal("20.00"),
            "overnight_penalty": Decimal("80.00"),
        },
        "OUTDOOR": {
            "members_only": False,
            "grace_minutes": 0,
            "weekday": {"per_entry_member": Decimal("2.00"), "per_entry_non_member": Decimal("4.00")},
            "weekend": {"per_entry_member": Decimal("1.00"), "per_entry_non_member": Decimal("3.00")},
            "public_holiday": {"per_entry_member": Decimal("1.00"), "per_entry_non_member": Decimal("3.00")},
            "overnight_penalty": Decimal("80.00"),
        },
        "VALET": {
            "members_only": False,
            "grace_minutes": 0,
            "weekday": {"first2h_flat": Decimal("10.00"), "per_hour": Decimal("15.00")},
            "weekend": {"first2h_flat": Decimal("15.00"), "per_hour": Decimal("15.00")},
            "public_holiday": {"first2h_flat": Decimal("20.00"), "per_hour": Decimal("15.00")},
            "overnight_penalty": Decimal("120.00"),
        },
        "STAFF": {
            "members_only": True,
            "grace_minutes": 0,
            "weekday": {"per_hour": Decimal("1.00")},
            "weekend": {"per_hour": Decimal("1.00")},
            "public_holiday": {"per_hour": Decimal("1.00")},
            "daily_cap": Decimal("7.00"),
            "overnight_penalty": Decimal("80.00"),
        },
    },

    # Memberships
    "memberships": {
        "NON-MEMBER": {"free_hours": 0, "daily_cap": None},
        "MEMBER": {"free_hours": 2, "daily_cap": None},
        "SILVER": {"free_hours": 4, "daily_cap": None},
        "GOLD": {"free_hours": 4, "daily_cap": Decimal("15.00")},
        "STAFF": {"free_hours": 0, "daily_cap": None},
    },

    # Penalties
    "penalties": {
        "lost_ticket": {
            "non_member": Decimal("50.00"),
            "member": Decimal("30.00"),
            "valet": Decimal("80.00"),
        },
    },

    # Validations
    "validations": {
        "partners": {
            "woolworths": {
                "min_spend": 30,
                "free_hours": 2,
            }
        }
    },
}
