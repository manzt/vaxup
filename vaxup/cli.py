import argparse
import datetime
import sys

from vaxup.utils import check as check_appointments
from vaxup.utils import enroll as enroll_appointments
from vaxup.utils import unenroll as unenroll_appointment
from vaxup.utils import check_id as check_appointment_id


def check(args: argparse.Namespace) -> None:
    check_appointments(date=args.date, fix=args.fix, show_all=args.show_all)


def enroll(args: argparse.Namespace) -> None:
    enroll_appointments(date=args.date, dry_run=args.dry_run)


def unenroll(args: argparse.Namespace) -> None:
    unenroll_appointment(acuity_id=args.acuity_id)


def check_id(args: argparse.Namespace) -> None:
    check_appointment_id(acuity_id=args.acuity_id, raw=args.raw)


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    # check
    parser_check = subparsers.add_parser("check")
    parser_check.add_argument("date", type=datetime.date.fromisoformat)
    parser_check.add_argument("--fix", action="store_true")
    parser_check.add_argument("--show-all", action="store_true")
    parser_check.set_defaults(func=check)

    # enroll
    parser_check = subparsers.add_parser("enroll")
    parser_check.add_argument("date", type=datetime.date.fromisoformat)
    parser_check.add_argument("--dry-run", action="store_true")
    parser_check.set_defaults(func=enroll)

    # unenroll
    parser_unenroll = subparsers.add_parser("unenroll")
    parser_unenroll.add_argument("acuity_id", type=int)
    parser_unenroll.set_defaults(func=unenroll)

    # check_id
    parser_check_id = subparsers.add_parser("check-id")
    parser_check_id.add_argument("acuity_id", type=int)
    parser_check_id.add_argument("--raw", action="store_true")
    parser_check_id.set_defaults(func=check_id)

    ns = parser.parse_args(sys.argv[1:])
    ns.func(ns)