import unittest
from decimal import Decimal
from src.fee_engine import compute_fee
from src.policy import POLICY


# 1) Grace boundary
class TestGraceBoundary(unittest.TestCase):
    def test_g1_under_grace_is_free(self):
        fee = compute_fee(
            duration_minutes=14, 
            zone="REGULAR",
            day_type="WEEKDAY", 
            member_tier="NON-MEMBER",
            validation=None, 
            lost_ticket=False, 
            policy=POLICY
        )
        self.assertEqual(fee.total, Decimal("0.00"))

    def test_g2_exactly_at_grace_charges_first_hour(self):
        fee = compute_fee(
            duration_minutes=15, 
            zone="REGULAR",
            day_type="WEEKDAY", 
            member_tier="NON-MEMBER",
            validation=None, 
            lost_ticket=False, 
            policy=POLICY
        )
        self.assertEqual(fee.total, Decimal("4.00"))
        
    def test_g3_one_min_after_grace_charges_first_hour(self):
        fee = compute_fee(
            duration_minutes=16, 
            zone="REGULAR",
            day_type="WEEKDAY", 
            member_tier="NON-MEMBER",
            validation=None, 
            lost_ticket=False, 
            policy=POLICY
        )
        self.assertEqual(fee.total, Decimal("4.00"))


# 2) 4:00AM cut-off penalty boundary
class TestCutoffPenalty(unittest.TestCase):
    def test_c1_exit_before_cutoff_no_penalty(self):
        fee = compute_fee(
            entry_at="2025-10-18T23:00", 
            exit_at="2025-10-19T03:59",
            duration_minutes=299, 
            zone="REGULAR",
            day_type="WEEKEND", 
            member_tier="NON-MEMBER",
            validation=None, 
            lost_ticket=False, 
            policy=POLICY
        )
        self.assertEqual(fee.penalties.overnight, Decimal("0.00"))
        self.assertEqual(fee.total, Decimal("10.00"))

    def test_c2_exit_exactly_4am_no_penalty(self):
        fee = compute_fee(
            entry_at="2025-10-18T23:00", 
            exit_at="2025-10-19T04:00",
            duration_minutes=300, 
            zone="REGULAR",
            day_type="WEEKEND", 
            member_tier="NON-MEMBER",
            validation=None, 
            lost_ticket=False, 
            policy=POLICY
        )
        self.assertEqual(fee.penalties.overnight, Decimal("0.00"))
        self.assertEqual(fee.total, Decimal("14.00"))

    def test_c3_exit_after_4am_triggers_penalty(self):
        fee = compute_fee(
            entry_at="2025-10-18T23:00", 
            exit_at="2025-10-19T04:01",
            duration_minutes=301, 
            zone="REGULAR",
            day_type="WEEKEND",
            member_tier="NON-MEMBER",
            validation=None, 
            lost_ticket=False, 
            policy=POLICY
        )
        self.assertEqual(fee.penalties.overnight, Decimal("80.00"))  
        self.assertEqual(fee.total, Decimal("94.00"))


# 3) Membership perks (free hours only; no discounts)
class TestMembershipFreeHours(unittest.TestCase):
    def test_m1_non_member_no_free_hours(self):
        fee = compute_fee(
            duration_minutes=180, 
            zone="REGULAR",
            day_type="WEEKDAY",
            member_tier="NON-MEMBER",
            validation=None,
            lost_ticket=False,
            policy=POLICY
        )
        # 3h weekday REGULAR: first 2h $4 + 3rd hour $4 = $8.00
        self.assertEqual(fee.total, Decimal("8.00"))

    def test_m2_member_two_free_hours(self):
        fee = compute_fee(
            duration_minutes=180, 
            zone="REGULAR",
            day_type="WEEKDAY",
            member_tier="MEMBER",
            validation=None,
            lost_ticket=False,
            policy=POLICY
        )
        # 3h weekday REGULAR: first 2h free -> pay 1h of $4 = $4.00
        self.assertEqual(fee.member_free_minutes, 120)
        self.assertEqual(fee.total, Decimal("4.00"))

    def test_m3_silver_four_free_hours(self):
        fee = compute_fee(
            duration_minutes=180, 
            zone="REGULAR",
            day_type="WEEKDAY",
            member_tier="SILVER",
            validation=None,
            lost_ticket=False,
            policy=POLICY
        )
        # 3h within 4h free -> $0.00
        self.assertEqual(fee.member_free_minutes, 240)
        self.assertEqual(fee.total, Decimal("0.00"))

    def test_m4_gold_daily_cap_and_free_hours(self):
        fee = compute_fee(
            duration_minutes=600,  # 10 hours
            zone="REGULAR",
            day_type="WEEKDAY",
            member_tier="GOLD",
            validation=None,
            lost_ticket=False,
            policy=POLICY
        )
        # 10h REGULAR = $4 (first 2h) + 8h*$4 = $36 -> Gold 4h free removes $12 -> $24, capped at $15
        self.assertEqual(fee.member_free_minutes, 240)
        self.assertEqual(fee.total, Decimal("15.00"))


# 4) Lost ticket penalties
class TestLostTicket(unittest.TestCase):
    def test_l1_non_member_lost_ticket(self):
        fee = compute_fee(
            duration_minutes=60,
            zone="REGULAR",
            day_type="WEEKDAY",
            member_tier="NON-MEMBER",
            validation=None,
            lost_ticket=True,
            policy=POLICY
        )
        self.assertEqual(fee.penalties.lost_ticket, Decimal("50.00"))
        self.assertEqual(fee.total, Decimal("50.00"))

    def test_l2_member_lost_onecard(self):
        fee = compute_fee(
            duration_minutes=60,
            zone="REGULAR",
            day_type="WEEKDAY",
            member_tier="MEMBER",
            validation=None,
            lost_ticket=True,
            policy=POLICY
        )
        self.assertEqual(fee.penalties.lost_ticket, Decimal("30.00"))
        self.assertEqual(fee.total, Decimal("30.00"))

    def test_l3_valet_lost_ticket(self):
        fee = compute_fee(
            duration_minutes=60,
            zone="VALET",
            day_type="WEEKDAY",
            member_tier="GOLD",
            validation=None,
            lost_ticket=True,
            policy=POLICY
        )
        self.assertEqual(fee.penalties.lost_ticket, Decimal("80.00"))
        self.assertEqual(fee.total, Decimal("80.00"))


# 5) Retailer validation (Woolworths only: spend >= $30 -> 2h free, stacks with membership perks)
class TestValidation(unittest.TestCase):
    """EP tests for Woolworths 2-hour validation, time-based (stacks after membership)."""

    def test_v1_non_member_weekday_6h_with_validation_is_16(self):
        validation = {"store": "Woolworths", "kind": "HOURS", "spend": 30}
        fee = compute_fee(
            duration_minutes=360,
            zone="REGULAR",
            day_type="WEEKDAY",
            member_tier="NON-MEMBER",
            validation=validation,
            lost_ticket=False,
            policy=POLICY,
        )
        # Validation removes 2h time -> pay 4h at $4 = $16
        self.assertEqual(fee.validation_hours, 2)
        self.assertEqual(fee.total, Decimal("16.00"))

    def test_v2_non_member_weekend_6h_with_validation_is_16(self):
        validation = {"store": "Woolworths", "kind": "HOURS", "spend": 30}
        fee = compute_fee(
            duration_minutes=360,
            zone="REGULAR",
            day_type="WEEKEND",
            member_tier="NON-MEMBER",
            validation=validation,
            lost_ticket=False,
            policy=POLICY,
        )
        # Validation removes 2h -> pay 4h at $4 = $16 
        self.assertEqual(fee.validation_hours, 2)
        self.assertEqual(fee.total, Decimal("16.00"))

    def test_v3_member_and_validation_stack_5h_is_4(self):
        validation = {"store": "Woolworths", "kind": "HOURS", "spend": 30}
        fee = compute_fee(
            duration_minutes=300,  # 5h total
            zone="REGULAR",
            day_type="WEEKDAY",
            member_tier="MEMBER",  # 2h free
            validation=validation,  # +2h free
            lost_ticket=False,
            policy=POLICY,
        )
        # 2 + 2 hours free -> 1 hour to pay -> $4
        self.assertEqual(fee.member_free_minutes, 120)
        self.assertEqual(fee.validation_hours, 2)
        self.assertEqual(fee.total, Decimal("4.00"))

    def test_v4_gold_with_validation_still_caps(self):
        validation = {"store": "Woolworths", "kind": "HOURS", "spend": 30}
        fee = compute_fee(
            duration_minutes=600,  # 10h
            zone="REGULAR",
            day_type="WEEKDAY",
            member_tier="GOLD",
            validation=validation,
            lost_ticket=False,
            policy=POLICY,
        )
        # 4h (member) + 2h (validation) = 6h free; pay 4h @ $4 = $16 -> cap $15
        self.assertEqual(fee.member_free_minutes, 240)
        self.assertEqual(fee.validation_hours, 2)
        self.assertEqual(fee.total, Decimal("15.00"))

    def test_v5_validation_not_applied_with_lost_ticket(self):
        validation = {"store": "Woolworths", "kind": "HOURS", "spend": 30}
        fee = compute_fee(
            duration_minutes=180,
            zone="REGULAR",
            day_type="WEEKDAY",
            member_tier="GOLD",
            validation=validation,
            lost_ticket=True,
            policy=POLICY,
        )
        self.assertEqual(fee.validation_hours, 0)
        self.assertEqual(fee.penalties.lost_ticket, Decimal("30.00"))
        self.assertEqual(fee.total, Decimal("30.00"))

    def test_v6_validation_not_allowed_in_valet(self):
        validation = {"store": "Woolworths", "kind": "HOURS", "spend": 30}
        fee = compute_fee(
            duration_minutes=120, #2h
            zone="VALET",
            day_type="WEEKDAY",
            member_tier="GOLD",
            validation=validation,
            lost_ticket=False,
            policy=POLICY,
        )
        # Valet weekday 2h -> $10
        self.assertEqual(fee.validation_hours, 0)
        self.assertEqual(fee. total, Decimal("10.00"))


# 6) Zone pricing
class TestZonePricing(unittest.TestCase):
    def test_z1_regular_weekday_first_2h_flat(self):
        fee = compute_fee(
            duration_minutes=120, 
            zone="REGULAR",
            day_type="WEEKDAY", 
            member_tier="NON-MEMBER",
            validation=None, 
            lost_ticket=False, 
            policy=POLICY
        )
        self.assertEqual(fee.total, Decimal("4.00"))

    def test_z2_regular_weekday_3h(self):
        fee = compute_fee(
            duration_minutes=181, 
            zone="REGULAR",
            day_type="WEEKDAY", 
            member_tier="NON-MEMBER",
            validation=None, 
            lost_ticket=False, 
            policy=POLICY
        )
        self.assertEqual(fee.total, Decimal("8.00"))

    def test_z3_regular_weekend_rates(self):
        fee = compute_fee(
            duration_minutes=120, 
            zone="REGULAR",
            day_type="WEEKEND", 
            member_tier="NON-MEMBER",
            validation=None, 
            lost_ticket=False, 
            policy=POLICY
        )
        self.assertEqual(fee.total, Decimal("2.00"))

    def test_z4_regular_public_holiday_rates(self):
        fee = compute_fee(
            duration_minutes=181, 
            zone="REGULAR",
            day_type="PUBLIC_HOLIDAY", 
            member_tier="NON-MEMBER",
            validation=None, 
            lost_ticket=False, 
            policy=POLICY
        )
        self.assertEqual(fee.total, Decimal("5.00"))

    def test_z5_preferred_member_zone_weekday(self):
        fee = compute_fee(
            duration_minutes=181, 
            zone="PREFERRED",
            day_type="WEEKDAY", 
            member_tier="GOLD",
            validation=None, 
            lost_ticket=False, 
            policy=POLICY
        )
        # Preferred weekday: first 2h $3 + next hour $4 = $7
        # Gold has 4 hours free -> $0
        self.assertEqual(fee.total, Decimal("0.00"))

    def test_z6_outdoor_non_member_weekday(self):
        fee = compute_fee(
            duration_minutes=10, 
            zone="OUTDOOR",
            day_type="WEEKDAY", 
            member_tier="NON-MEMBER",
            validation=None, 
            lost_ticket=False, 
            policy=POLICY
        )
        # Per entry: $4/h
        self.assertEqual(fee.total, Decimal("4.00"))
        
    def test_z7_outdoor_member_weekday(self):
        fee = compute_fee(
            duration_minutes=10, 
            zone="OUTDOOR",
            day_type="WEEKDAY", 
            member_tier="MEMBER",
            validation=None, 
            lost_ticket=False, 
            policy=POLICY
        )
        # Per entry: $2/h
        self.assertEqual(fee.total, Decimal("2.00"))

    def test_z8_valet_2h_flat(self):
        fee = compute_fee(
            duration_minutes=120, 
            zone="VALET",
            day_type="WEEKDAY", 
            member_tier="NON-MEMBER",
            validation=None, 
            lost_ticket=False, 
            policy=POLICY
        )
        self.assertEqual(fee.total, Decimal("10.00"))
        
    def test_z9_valet_after_2h_rate(self):
        fee = compute_fee(
            duration_minutes=181, # 3h
            zone="VALET",
            day_type="WEEKDAY", 
            member_tier="NON-MEMBER",
            validation=None, 
            lost_ticket=False, 
            policy=POLICY
        )
        # Weekday first 2h $10 + remaining hours $15/h -> $25
        self.assertEqual(fee.total, Decimal("25.00"))

    def test_z10_staff_zone_flat_rate(self):
        fee = compute_fee(
            duration_minutes=60, 
            zone="STAFF",
            day_type="WEEKDAY", 
            member_tier="STAFF",
            validation=None, 
            lost_ticket=False, 
            policy=POLICY
        )
        self.assertEqual(fee.total, Decimal("1.00"))
        
    def test_z11_staff_zone_with_cap(self):
        fee = compute_fee(
            duration_minutes=480, # 8h
            zone="STAFF",
            day_type="WEEKDAY", 
            member_tier="STAFF",
            validation=None, 
            lost_ticket=False, 
            policy=POLICY
        )
        self.assertEqual(fee.total, Decimal("7.00"))  # daily cap
