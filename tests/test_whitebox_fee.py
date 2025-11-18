import unittest
from decimal import Decimal
from src.fee_engine import compute_fee
from src.policy import POLICY


class TestWhiteBoxFee(unittest.TestCase):
    """Covers remaining branches and exceptional cases."""

    def test_w1_missing_policy_returns_zero(self):
        fee = compute_fee(
            duration_minutes=60, 
            zone="REGULAR", 
            day_type="WEEKDAY", 
            policy=None
            )
        self.assertEqual(fee.total, Decimal("0.00"))

    def test_w2_staff_lost_ticket_treated_as_member(self):
        fee = compute_fee(
            duration_minutes=60, 
            zone="REGULAR", 
            day_type="WEEKDAY",
            member_tier="STAFF", 
            lost_ticket=True, 
            policy=POLICY
            )
        self.assertEqual(fee.total, Decimal("30.00"))
        
    def test_w3_validation_not_partners(self):
        validation = {"store": "Coles", "kind": "HOURS", "spend": 30}
        fee = compute_fee(
            duration_minutes=360, # 6h
            zone="REGULAR",
            day_type="WEEKDAY",
            member_tier="NON-MEMBER",
            validation=validation,
            lost_ticket=False,
            policy=POLICY,
        )
        self.assertEqual(fee.validation_hours, 0)
        self.assertEqual(fee.total, Decimal("20.00"))
        
    def test_w4_validation_below_min_spend(self):
        validation = {"store": "Woolworths", "kind": "HOURS", "spend": 20}
        fee = compute_fee(
            duration_minutes=360, # 6h
            zone="REGULAR",
            day_type="WEEKDAY",
            member_tier="NON-MEMBER",
            validation=validation,
            lost_ticket=False,
            policy=POLICY,
        )
        self.assertEqual(fee.validation_hours, 0)
        self.assertEqual(fee.total, Decimal("20.00"))

    def test_w5_preferred_weekend(self):
        fee = compute_fee(
            duration_minutes=60, 
            zone="PREFERRED", 
            day_type="WEEKEND",
            member_tier="MEMBER", 
            policy=POLICY
            )
        self.assertEqual(fee.total, Decimal("0.00"))
        
    def test_w6_preferred_public_holiday(self):
        fee = compute_fee(
            duration_minutes=300, 
            zone="PREFERRED", 
            day_type="PUBLIC_HOLIDAY",
            member_tier="MEMBER", 
            policy=POLICY
            )
        self.assertEqual(fee.total, Decimal("6.00"))

    def test_w7_outdoor_weekend(self):
        fee = compute_fee(
            duration_minutes=10, 
            zone="OUTDOOR", 
            day_type="WEEKEND",
            member_tier="NON-MEMBER", 
            policy=POLICY
            )
        self.assertEqual(fee.total, Decimal("3.00"))  

    def test_w8_outdoor_public_holiday(self):
        fee = compute_fee(
            duration_minutes=10, 
            zone="OUTDOOR", 
            day_type="PUBLIC_HOLIDAY",
            member_tier="NON-MEMBER", 
            policy=POLICY
            )
        self.assertEqual(fee.total, Decimal("3.00"))  

    def test_w9_valet_weekend(self):
        fee = compute_fee(
            duration_minutes=50, 
            zone="VALET", 
            day_type="WEEKEND",
            member_tier="MEMBER", 
            policy=POLICY
            )
        self.assertEqual(fee.total, Decimal("15.00"))  
        
    def test_w10_valet_public_holiday(self):
        fee = compute_fee(
            duration_minutes=181, 
            zone="VALET", 
            day_type="PUBLIC_HOLIDAY",
            member_tier="MEMBER", 
            policy=POLICY
            )
        self.assertEqual(fee.total, Decimal("35.00"))  

    def test_w11_staff_weekend_rate(self):
        fee = compute_fee(
            duration_minutes=120, 
            zone="STAFF", 
            day_type="WEEKEND",
            member_tier="STAFF", 
            policy=POLICY
            )
        self.assertEqual(fee.total, Decimal("2.00"))

    def test_w12_staff_public_holiday_rate(self):
        fee = compute_fee(
            duration_minutes=120, 
            zone="STAFF", 
            day_type="PUBLIC_HOLIDAY",
            member_tier="STAFF", 
            policy=POLICY
            )
        self.assertEqual(fee.total, Decimal("2.00"))  

    def test_w13_invalid_timestamps_in_cutoff(self):
        """Force exception branch of overnight penalty logic."""
        fee = compute_fee(
            duration_minutes=60,
            zone="REGULAR",
            day_type="WEEKDAY",
            member_tier="NON-MEMBER",
            entry_at="not-a-date",
            exit_at="not-a-date",
            policy=POLICY,
        )
        self.assertEqual(fee.total, Decimal("4.00"))  # fallback path
