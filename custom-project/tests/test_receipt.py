import unittest
from decimal import Decimal
from approvaltests import verify, Options
from approvaltests.scrubbers import create_regex_scrubber

from src.fee_engine import compute_fee
from src.policy import POLICY
from src.ui import print_receipt_output


def approve_receipt(text: str):
    # Stabilise volatile fields so snapshots dont churn.
    scrub_id = create_regex_scrubber(r"Receipt ID\s*: RCP-.*",
                                     "Receipt ID       : RCP-XXXXX")
    verify(text, options=Options().with_scrubber(scrub_id))


class TestReceiptApproval(unittest.TestCase):
    def test_a1_receipt_non_member_weekday(self):
        """REGULAR, WEEKDAY, NON-MEMBER, 2h30m."""
        fee = compute_fee(
            duration_minutes=150,  # 2h 30m
            zone="REGULAR",
            day_type="WEEKDAY",
            member_tier="NON-MEMBER",
            validation=None,
            lost_ticket=False,
            policy=POLICY,
            entry_at="2025-10-18T10:15",
            exit_at="2025-10-18T12:45",
        )
        text = print_receipt_output(
            ticket_id=1234,
            zone="REGULAR",
            member_tier="NON-MEMBER",
            fee=fee,
            day_type="WEEKDAY",
            entry_at="2025-10-18T10:15",
            exit_at="2025-10-18T12:45",
            duration_minutes=150,
            validation=None,
            return_str=True,
        )
        approve_receipt(text)

    def test_a2_receipt_member_with_validation(self):
        """REGULAR, WEEKDAY, MEMBER, 3h, Woolworths ≥ $30 (stack: member 2h + validation 2h)."""
        validation = {"store": "Woolworths", "kind": "HOURS", "spend": 35}
        fee = compute_fee(
            duration_minutes=180,  # 3h
            zone="REGULAR",
            day_type="WEEKDAY",
            member_tier="MEMBER",
            validation=validation,
            lost_ticket=False,
            policy=POLICY,
            entry_at="2025-10-18T11:00",
            exit_at="2025-10-18T14:00",
        )
        text = print_receipt_output(
            ticket_id=2234,
            zone="REGULAR",
            member_tier="MEMBER",
            fee=fee,
            day_type="WEEKDAY",
            entry_at="2025-10-18T11:00",
            exit_at="2025-10-18T14:00",
            duration_minutes=180,
            validation=validation,
            return_str=True,
        )
        approve_receipt(text)

    def test_a3_receipt_lost_ticket(self):
        """Lost ticket path - show Duration: N/A, total from penalty table."""
        fee = compute_fee(
            duration_minutes=0,    # ignored in engine when lost_ticket=True
            zone="REGULAR",
            day_type="WEEKDAY",
            member_tier="NON-MEMBER",
            validation=None,
            lost_ticket=True,
            policy=POLICY,
            entry_at="2025-10-18T15:10",
            exit_at="LOST TICKET",
        )
        # For N/A duration we pass duration_minutes=None to the renderer.
        text = print_receipt_output(
            ticket_id=3333,
            zone="REGULAR",
            member_tier="NON-MEMBER",
            fee=fee,
            day_type="WEEKDAY",
            entry_at="2025-10-18T15:10",
            exit_at="LOST TICKET",
            duration_minutes=None,
            validation=None,
            return_str=True,
        )
        approve_receipt(text)

    def test_a4_receipt_gold_member_capped(self):
        """REGULAR, WEEKDAY, GOLD, 10h - capped at $15 with 4h free."""
        fee = compute_fee(
            duration_minutes=600,  # 10h
            zone="REGULAR",
            day_type="WEEKDAY",
            member_tier="GOLD",
            validation=None,
            lost_ticket=False,
            policy=POLICY,
            entry_at="2025-10-18T08:00",
            exit_at="2025-10-18T18:00",
        )
        # Sanity check the engine math in-line to keeps snapshot meaningful.
        self.assertEqual(fee.total, Decimal("15.00"))

        text = print_receipt_output(
            ticket_id=4444,
            zone="REGULAR",
            member_tier="GOLD",
            fee=fee,
            day_type="WEEKDAY",
            entry_at="2025-10-18T08:00",
            exit_at="2025-10-18T18:00",
            duration_minutes=600,
            validation=None,
            return_str=True,
        )
        approve_receipt(text)
