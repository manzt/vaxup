import argparse
import datetime
import sys

from .utils import check as check_appointments
from .utils import enroll as enroll_appointments


def check(args: argparse.Namespace) -> None:
    check_appointments(date=args.date, fix=args.fix, show_all=args.show_all)


def enroll(args: argparse.Namespace) -> None:
    enroll_appointments(date=args.date, dry_run=args.dry_run)


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

    ns = parser.parse_args(sys.argv[1:])
    ns.func(ns)
