# src/ui.py
from datetime import datetime
from src.fee_engine import compute_fee
from src.policy import POLICY
from src.data_manager import load_tickets

def main():
    print("\n============================================")
    print("        Shopping Mall Parking System        ")
    print("============================================")
    while True:
        print("\nSelect an action:")
        print("1. Compute fee manually")
        print("2. Compute fee from existing record")
        print("3. Print receipt (completed tickets)")
        print("4. Exit\n")
        choice = input(">> ").strip()

        if choice == "1":
            compute_fee_manual()
        elif choice == "2":
            compute_from_pending()
        elif choice == "3":
            print_receipt()
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid choice.")

def compute_fee_manual():
    def prompt_choice(prompt, options):
        opts_str = "/".join(options)
        while True:
            s = input(f"{prompt} ({opts_str}): ").strip().upper()
            if s in options:
                return s
            print(f"Invalid input. Please enter one of: {opts_str}")

    def prompt_yes_no(prompt):
        while True:
            s = input(f"{prompt} (Y/N): ").strip().upper()
            if s in ("Y", "N"):
                return s == "Y"
            print("Invalid input. Please enter Y or N.")

    def prompt_int(prompt, min_val=None, max_val=None):
        while True:
            s = input(f"{prompt}: ").strip()
            try:
                v = int(s)
                if min_val is not None and v < min_val:
                    print(f"Please enter an integer greater or equal to {min_val}.")
                    continue
                return v
            except ValueError:
                print("Invalid number. Please enter an integer.")

    def prompt_float(prompt):
        while True:
            s = input(f"{prompt}: ").strip()
            try:
                v = float(s)
                if v < 0:
                    print("Value must be >= 0.")
                    continue
                return v
            except ValueError:
                print("Invalid number. Please enter a numeric amount.")

    # allowed enums
    TIERS = {"NON-MEMBER", "MEMBER", "SILVER", "GOLD", "STAFF"}
    ZONES = {"REGULAR", "PREFERRED", "OUTDOOR", "VALET", "STAFF"}
    DAYS  = {"WEEKDAY", "WEEKEND", "PUBLIC_HOLIDAY"}

    tier = prompt_choice("Membership tier", TIERS)
    zone = prompt_choice("Zone", ZONES)
    day_type = prompt_choice("Day type", DAYS)
    lost_ticket = prompt_yes_no("Lost ticket")

    duration = None
    validation = None

    if not lost_ticket:
        duration = prompt_int("Duration in minutes", min_val=0)

        # Only offer validation for zones that support it
        if zone in {"REGULAR", "PREFERRED", "STAFF"}:
            if prompt_yes_no("Validation"):
                partners = set(POLICY["validations"]["partners"].keys())
                print(f"Available validation partners: {', '.join(sorted(p.title() for p in partners))}")
                while True:
                    store_in = input("Store name: ").strip().lower()
                    if store_in in partners:
                        break
                    print("Invalid store. Please choose a configured partner.")
                spend = prompt_float("Spend amount")
                validation = {"store": store_in.title(), "kind": "HOURS", "spend": spend}

    # demo timestamps
    now = datetime.now()
    entry_at = now.replace(hour=12, minute=0).isoformat(timespec="minutes")
    exit_at  = now.replace(hour=16, minute=10).isoformat(timespec="minutes")

    fee = compute_fee(
        duration_minutes=duration or 0,
        zone=zone,
        day_type=day_type,
        member_tier=tier,
        validation=validation,
        lost_ticket=lost_ticket,
        entry_at=entry_at,
        exit_at=exit_at,
        policy=POLICY
    )

    print_receipt_output(
        ticket_id=None,
        zone=zone,
        member_tier=tier,
        fee=fee,
        day_type=day_type,
        entry_at=entry_at,
        exit_at=exit_at,
        duration_minutes=duration,
        validation=validation
    )

def compute_from_pending():
    tickets = load_tickets("tickets_pending.json")
    if not tickets:
        print("No pending tickets found.")
        return

    print("\nPending tickets:")
    for t in tickets:
        print(f"{t['ticket_id']} | {t['zone']} | {t['member_tier']} | Entered {t['entry_time']}")

    try:
        tid = int(input("\nEnter Ticket ID: "))
    except ValueError:
        print("Invalid ID.")
        return

    ticket = next((t for t in tickets if t["ticket_id"] == tid), None)
    if not ticket:
        print("Ticket not found.")
        return

    print("\nTicket Details")
    print("------------------------------")
    for k in ("ticket_id", "zone", "member_tier", "entry_time", "day_type", "validation", "lost_ticket"):
        print(f"{k.replace('_',' ').title():<16}: {ticket.get(k)}")

    print("\nSelect an action:")
    print("1. Report Lost Ticket")
    print("2. Enter Exit Time and Calculate Fee")
    print("3. Cancel\n")
    choice = input(">> ").strip()

    if choice == "1":
        ticket["lost_ticket"] = True
        exit_at = "LOST TICKET"
        duration = None
    elif choice == "2":
        while True:
            exit_at = input("Enter exit time (YYYY-MM-DDTHH:MM): ").strip()
            try:
                entry_dt = datetime.fromisoformat(ticket["entry_time"])
                exit_dt = datetime.fromisoformat(exit_at)
                # handle wrong sequence (exit before entry)
                if exit_dt < entry_dt:
                    print("Exit time cannot be earlier than entry time.")
                    continue
                delta = exit_dt - entry_dt
                duration = int(delta.total_seconds() // 60)
                print(f"Calculated duration: {duration} minutes")
                break
            except ValueError:
                print("Invalid datetime format. Please try again.")
    else:
        return

    fee = compute_fee(
        duration_minutes=duration or 0,
        zone=ticket["zone"],
        day_type=ticket["day_type"],
        member_tier=ticket["member_tier"],
        validation=ticket["validation"],
        lost_ticket=ticket["lost_ticket"],
        entry_at=ticket["entry_time"],
        exit_at=exit_at,
        policy=POLICY,
    )
    print_receipt_output(
        ticket_id=ticket["ticket_id"],
        zone=ticket["zone"],
        member_tier=ticket["member_tier"],
        fee=fee,
        day_type=ticket["day_type"],
        entry_at=ticket["entry_time"],
        exit_at=exit_at,
        duration_minutes=duration,
        validation=ticket["validation"],
    )

def print_receipt():
    tickets = load_tickets("tickets_completed.json")
    if not tickets:
        print("No completed tickets found.")
        return

    print("\nAvailable receipts:")
    for t in tickets:
        tag = "LOST TICKET" if t["lost_ticket"] else f"Total: ${t['total']:.2f}"
        print(f"{t['ticket_id']} | {t['zone']} | {t['member_tier']} | {tag}")

    try:
        tid = int(input("\nEnter ticket ID to view: "))
    except ValueError:
        print("Invalid ID.")
        return

    ticket = next((t for t in tickets if t["ticket_id"] == tid), None)
    if not ticket:
        print("Ticket not found.")
        return

    fee = compute_fee(
        duration_minutes=ticket.get("duration_minutes") or 0,
        zone=ticket["zone"],
        day_type=ticket["day_type"],
        member_tier=ticket["member_tier"],
        validation=ticket.get("validation"),
        lost_ticket=ticket["lost_ticket"],
        entry_at=ticket.get("entry_time"),
        exit_at=ticket.get("exit_time"),
        policy=POLICY
    )

    print_receipt_output(
        ticket_id=ticket["ticket_id"],
        zone=ticket["zone"],
        member_tier=ticket["member_tier"],
        fee=fee,
        day_type=ticket["day_type"],
        entry_at=ticket.get("entry_time"),
        exit_at=ticket.get("exit_time") or "LOST TICKET",
        duration_minutes=ticket.get("duration_minutes"),
        validation=ticket.get("validation"),
    )

def print_receipt_output(ticket_id=None,
                         zone=None,
                         member_tier=None,
                         fee=None,
                         day_type=None,
                         entry_at=None,
                         exit_at=None,
                         duration_minutes=None,
                         validation=None,
                         return_str=False):
    """Pretty-print a 1U-style parking receipt. If return_str=True, returns the text."""
    # duration display
    if duration_minutes is not None:
        hours = duration_minutes // 60
        mins = duration_minutes % 60
        duration_display = f"{hours}h {mins}m"
    else:
        duration_display = "N/A"

    # validation display (checks spend threshold)
    if validation:
        store = validation.get("store", "").lower()
        spend = validation.get("spend", 0)
        partners = {"woolworths": 30}
        if store in partners and spend >= partners[store]:
            validation_display = "2 FREE HOURS"
        else:
            validation_display = "NONE"
    else:
        validation_display = "NONE"

    # free hours display (membership perks)
    free_hours = getattr(fee, "member_free_minutes", 0) // 60
    free_hours_display = f"{free_hours}h" if free_hours else "NONE"

    rid = f"RCP-{ticket_id or datetime.now().strftime('%H%M%S')}"
    lines = [
        "==============================================",
        "             1U PARKING RECEIPT               ",
        "==============================================",
        f"Receipt ID       : {rid}",
        f"Ticket ID        : T-{ticket_id or 'XXXXXX'}",
        "",
        "----------------------------------------------",
        "Customer / Ticket",
        "----------------------------------------------",
        f"Ticket Type        : PAPER TICKET",
        f"Membership Tier    : {member_tier or 'N/A'}",
        "",
        "----------------------------------------------",
        "Parking Details",
        "----------------------------------------------",
        f"Zone               : {zone or 'N/A'}",
        f"Day Type           : {day_type or 'N/A'}",
        f"Entry Date/Time    : {entry_at or 'N/A'}",
        f"Exit  Date/Time    : {exit_at or 'N/A'}",
        f"Duration           : {duration_display}",
        "",
        "----------------------------------------------",
        "Charges Breakdown",
        "----------------------------------------------",
        f"Time Charge            : ${fee.time_charge:.2f}",
        f"Free Hours (Tier Perk) : {free_hours_display}",
        f"Validation             : {validation_display}",
        "----------------------------------------------",
        f"TOTAL DUE              : ${fee.total:.2f}",
        f"AMOUNT PAID            : ${fee.total:.2f}",
        "----------------------------------------------",
        "Thank you for visiting 1U Shopping Centre!",
        "For assistance, contact support@1uparking.my",
        "==============================================",
    ]
    output = "\n".join(lines)
    if return_str:
        return output
    print(output)
