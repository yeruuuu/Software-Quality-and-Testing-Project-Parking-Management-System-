from decimal import Decimal
import math
from datetime import datetime, time


class Fee:
    """Encapsulates all computed fee details (used by tests)."""

    def __init__(self):
        self.total = Decimal("0.00")
        self.time_charge = Decimal("0.00")
        self.member_free_minutes = 0
        self.validation_hours = 0
        self.penalties = type(
            "Penalties",
            (),
            {"overnight": Decimal("0.00"), "lost_ticket": Decimal("0.00")},
        )


def compute_fee(
    duration_minutes=None,
    zone=None,
    day_type=None,
    member_tier=None,
    validation=None,
    lost_ticket=False,
    policy=None,
    entry_at=None,
    exit_at=None,
):
    """
    Compute total parking fee based on duration, zone, membership tier, and rules in policy.
    """
    fee = Fee()

    # Step 1: Handle empty inputs 
    if not policy or not zone or not day_type or duration_minutes is None:
        return fee

    # Step 2: Apply lost-ticket penalty  
    if lost_ticket:
        lt = policy["penalties"]["lost_ticket"]
        if zone == "VALET":
            penalty = lt["valet"]
        else:
            is_member = member_tier in ("MEMBER", "SILVER", "GOLD", "STAFF")
            penalty = lt["member"] if is_member else lt["non_member"]
        fee.penalties.lost_ticket = penalty
        fee.time_charge = Decimal("0.00")
        fee.total = penalty
        return fee

    # Step 3: Grace period 
    grace = policy["zones"][zone]["grace_minutes"]
    if duration_minutes < grace:
        fee.total = Decimal("0.00")
        return fee

    # Step 4: Compute hours (round down) 
    hours = math.floor(duration_minutes / 60)
    # to handle under 60 minutes 
    if hours == 0: 
        hours = 1

    # Step 5a: Apply membership perks 
    member_check = policy["memberships"].get(member_tier, {"free_hours": 0, "daily_cap": None})
    free_hours = int(member_check.get("free_hours", 0))
    fee.member_free_minutes = free_hours * 60
    
    # Step 5b: Apply retailer validation 
    validation_hours = 0
    if validation and not lost_ticket and zone not in ("VALET", "OUTDOOR"):
        # check if Woolworths and spend >= threshold
        store = validation.get("store", "").lower()
        spend = validation.get("spend", 0)
        partners = policy["validations"]["partners"]
        if store in partners:
            v = partners[store]
            if spend >= v["min_spend"]:
                validation_hours = v["free_hours"]

    fee.validation_hours = validation_hours

    # total free hours = membership + validation (stacked)
    # Membership free-hours apply to REGULAR and PREFERRED (not OUTDOOR/VALET). STAFF has 0 free hours anyway.
    # Validation hours apply to REGULAR, PREFERRED, STAFF (not VALET/OUTDOOR).
    if zone in ("REGULAR", "PREFERRED"):
        total_free_hours = free_hours + validation_hours
    elif zone == "STAFF":
        total_free_hours = validation_hours
    else:
        total_free_hours = 0

    # only apply free hours for time-based zones (not Outdoor or Valet)
    if zone not in ("OUTDOOR", "VALET"):
        hours_to_bill = max(hours - total_free_hours, 0)
    else:
        hours_to_bill = hours

    # Step 6: Zone-based pricing
    time_charge = Decimal("0.00")

    # REGULAR (weekday, weekend, public holiday)
    if zone == "REGULAR":
        rates = policy["zones"][zone]
        if day_type == "WEEKDAY":
            rate = rates["weekday"]
        elif day_type == "WEEKEND":
            rate = rates["weekend"]
        elif day_type == "PUBLIC_HOLIDAY":
            rate = rates["public_holiday"]
        else:
            # Fallback if unspecified
            rate = rates["weekday"]

        # Free hours remove the flat 2h block if they cover it.
        if hours_to_bill <= 0:
            time_charge = Decimal("0.00")
        elif total_free_hours >= 2:
            # already skipped first-2h flat; charge only remaining at per-hour rate
            time_charge = rate["per_hour"] * hours_to_bill
        elif hours_to_bill <= 2 - total_free_hours:
            # still within discounted 2h bundle after partial free time
            time_charge = rate["first2h_flat"]
        else:
            # partially consume flat, then per-hour for remainder
            remaining_after_flat = hours_to_bill - (2 - total_free_hours)
            time_charge = rate["first2h_flat"] + remaining_after_flat * rate["per_hour"]
            
    # Preferred (members-only)
    elif zone == "PREFERRED":
        rates = policy["zones"][zone]
        if day_type == "WEEKDAY":
            rate = rates["weekday"]
        elif day_type == "WEEKEND":
            rate = rates["weekend"]
        elif day_type == "PUBLIC_HOLIDAY":
            rate = rates["public_holiday"]
        else:
            rate = rates["weekday"]

        if hours_to_bill <= 0:
            time_charge = Decimal("0.00")
        else:
            time_charge = rate["per_hour"] * hours_to_bill

    # Outdoor (per-entry style)
    elif zone == "OUTDOOR":
        rates = policy["zones"][zone]
        if day_type == "WEEKDAY":
            base = rates["weekday"]
        elif day_type == "WEEKEND":
            base = rates["weekend"]
        elif day_type == "PUBLIC_HOLIDAY":
            base = rates["public_holiday"]
        else:
            base = rates["weekday"]

        if member_tier in ("MEMBER", "SILVER", "GOLD"):
            time_charge = base["per_entry_member"]
        else:
            time_charge = base["per_entry_non_member"]

    # Valet
    elif zone == "VALET":
        rates = policy["zones"][zone]
        if day_type == "WEEKDAY":
            rate = rates["weekday"]
        elif day_type == "WEEKEND":
            rate = rates["weekend"]
        elif day_type == "PUBLIC_HOLIDAY":
            rate = rates["public_holiday"]
        else:
            rate = rates["weekday"]

        if hours <= 2:
            time_charge = rate["first2h_flat"]
        else:
            time_charge = rate["first2h_flat"] + (hours - 2) * rate["per_hour"]

    # Staff
    elif zone == "STAFF":
        rates = policy["zones"][zone]
        if day_type == "WEEKDAY":
            rate = rates["weekday"]["per_hour"]
        elif day_type == "WEEKEND":
            rate = rates["weekend"]["per_hour"]
        elif day_type == "PUBLIC_HOLIDAY":
            rate = rates["public_holiday"]["per_hour"]
        else:
            rate = policy["zones"][zone]["weekday"]["per_hour"]

        time_charge = rate * hours_to_bill

        cap = policy["zones"][zone].get("daily_cap")
        time_charge = min(time_charge, cap)

    # Step 7: Apply member and zone caps
    member_cap = member_check.get("daily_cap")
    if zone != "VALET" and member_cap is not None:
        time_charge = min(time_charge, member_cap)

    zone_cap = policy["zones"][zone].get("daily_cap")
    if zone_cap is not None:
        time_charge = min(time_charge, zone_cap)
        
    # Step 7b: Apply 4:00 AM cut-off penalty (stacks with duration fee)
    fee.penalties.overnight = Decimal("0.00")
    if entry_at and exit_at:
        try:
            entry_dt = datetime.fromisoformat(entry_at)
            exit_dt = datetime.fromisoformat(exit_at)

            if exit_dt.date() > entry_dt.date():
                cutoff_hour, cutoff_min = map(int, policy["cutoff_time"].split(":"))
                cutoff_time = time(cutoff_hour, cutoff_min)
                if exit_dt.time() > cutoff_time:
                    penalty = policy["zones"][zone]["overnight_penalty"]
                    fee.penalties.overnight = penalty
                    fee.total = time_charge + penalty
                    return fee
        except Exception:
            fee.total = time_charge


    # Step 8: Assign and return
    fee.time_charge = time_charge
    fee.total = time_charge
    return fee
