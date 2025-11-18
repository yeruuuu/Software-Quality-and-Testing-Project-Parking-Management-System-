import unittest
from unittest import mock
from decimal import Decimal
from src import ui


class FakeFee:
    """Minimal stand-in for compute_fee return value."""
    def __init__(self, total, time_charge=None, member_free_minutes=0):
        self.total = Decimal(str(total))
        self.time_charge = Decimal(str(time_charge if time_charge is not None else total))
        self.member_free_minutes = member_free_minutes


class TestMockedUI(unittest.TestCase):
    @mock.patch("src.ui.compute_fee")
    @mock.patch("builtins.input")
    def test_mo1_manual_compute_fee_called_once_with_args(self, inp, mock_fee):
        inp.side_effect = ["MEMBER", "REGULAR", "WEEKDAY", "N", "120", "Y", "Woolworths", "35"]
        mock_fee.return_value = FakeFee(total="12.00", time_charge="12.00", member_free_minutes=120)

        ui.compute_fee_manual()

        mock_fee.assert_called_once()
        _, kwargs = mock_fee.call_args
        self.assertEqual(kwargs["zone"], "REGULAR")
        self.assertEqual(kwargs["member_tier"], "MEMBER")
        self.assertFalse(kwargs["lost_ticket"])
        self.assertEqual(kwargs["validation"]["store"], "Woolworths")
        self.assertEqual(kwargs["validation"]["spend"], 35.0)

    @mock.patch("src.ui.load_tickets")
    @mock.patch("src.ui.compute_fee")
    @mock.patch("builtins.input")
    def test_mo2_print_receipt_recomputes(self, inp, mock_fee, mock_load):
        mock_load.return_value = [{
            "ticket_id": 101, "zone": "REGULAR", "member_tier": "SILVER",
            "entry_time": "2025-10-18T10:00", "exit_time": "2025-10-18T15:00",
            "duration_minutes": 300, "day_type": "WEEKDAY",
            "validation": None, "lost_ticket": False, "total": 999  # ignored
        }]
        inp.side_effect = ["101"]
        mock_fee.return_value = FakeFee(total="20.00", time_charge="20.00")

        ui.print_receipt()

        mock_fee.assert_called_once()
        _, kwargs = mock_fee.call_args
        self.assertEqual(kwargs["duration_minutes"], 300)
        self.assertEqual(kwargs["zone"], "REGULAR")
        self.assertEqual(kwargs["member_tier"], "SILVER")
        self.assertFalse(kwargs["lost_ticket"])

    @mock.patch("src.ui.load_tickets")
    @mock.patch("src.ui.compute_fee")
    @mock.patch("builtins.input")
    def test_mo3_pending_auto_duration(self, inp, mock_fee, mock_load):
        mock_load.return_value = [{
            "ticket_id": 200, "zone": "REGULAR", "member_tier": "MEMBER",
            "entry_time": "2025-10-18T10:00", "day_type": "WEEKDAY",
            "validation": None, "lost_ticket": False
        }]
        inp.side_effect = ["200", "2", "2025-10-18T13:00"]  # option 2 -> exit 3h later
        mock_fee.return_value = FakeFee(total="12.00", time_charge="12.00")

        ui.compute_from_pending()
        _, kwargs = mock_fee.call_args
        self.assertEqual(kwargs["duration_minutes"], 180)

    @mock.patch("src.ui.load_tickets")
    @mock.patch("src.ui.compute_fee")
    @mock.patch("builtins.input")
    def test_mo4_pending_lost_ticket_sets_flag(self, inp, mock_fee, mock_load):
        mock_load.return_value = [{
            "ticket_id": 300, "zone": "REGULAR", "member_tier": "MEMBER",
            "entry_time": "2025-10-18T10:00", "day_type": "WEEKDAY",
            "validation": None, "lost_ticket": False
        }]
        inp.side_effect = ["300", "1"]  # choose "Report Lost Ticket"
        mock_fee.return_value = FakeFee(total="30.00", time_charge="0.00")

        ui.compute_from_pending()
        _, kwargs = mock_fee.call_args
        self.assertTrue(kwargs["lost_ticket"])
        self.assertEqual(kwargs["duration_minutes"], 0)

    @mock.patch("src.ui.compute_fee")
    @mock.patch("builtins.input")
    def test_mo5_reprompt_invalid_to_valid(self, inp, mock_fee):
        inp.side_effect = [
            "VIP", "GOLD",              # tier invalid -> valid
            "BASEMENT", "REGULAR",      # zone invalid -> valid
            "HOLIDAY", "WEEKDAY",       # day invalid -> valid
            "N", "60", "N"              # rest of prompts
        ]
        mock_fee.return_value = FakeFee(total="5.00", time_charge="5.00")

        ui.compute_fee_manual()
        mock_fee.assert_called_once()

    @mock.patch("src.ui.load_tickets", return_value=[])
    def test_mo6_no_pending_tickets(self, _load):
        ui.compute_from_pending()  # should not crash

    @mock.patch("src.ui.load_tickets")
    @mock.patch("src.ui.compute_fee")
    @mock.patch("builtins.input")
    def test_mo7_exit_before_entry_then_ok(self, inp, mock_fee, mock_load):
        mock_load.return_value = [{
            "ticket_id": 777, "zone": "REGULAR", "member_tier": "MEMBER",
            "entry_time": "2025-10-18T10:00", "day_type": "WEEKDAY",
            "validation": None, "lost_ticket": False
        }]
        inp.side_effect = ["777", "2", "2025-10-18T09:00", "2025-10-18T12:00"]  # invalid then valid
        mock_fee.return_value = FakeFee(total="8.00", time_charge="8.00")

        ui.compute_from_pending()
        _, kwargs = mock_fee.call_args
        self.assertEqual(kwargs["duration_minutes"], 120)
