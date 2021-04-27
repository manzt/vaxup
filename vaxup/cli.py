import argparse
import datetime
import os
import sys

from pydantic import ValidationError
from rich.console import Console
from rich.prompt import Prompt

from vaxup.acuity import edit_appointment, get_appointments
from vaxup.data import FormEntry, DUMMY_DATA
from vaxup.web import AuthorizedEnroller


def fmt_err(e, record):
    fields = []
    for err in e.errors():
        field = err["loc"][0]
        fields.append({field: record[field]})
    date = datetime.datetime.strptime(record["start_time"], "%Y-%m-%dT%H:%M:%S%z")
    date = date.strftime("%Y-%m-%d @ %I:%M %p")
    return f"[red bold]Error[/red bold] - id={record.get('id')} {date=} {fields=}"


def check(args: argparse.Namespace) -> None:
    console = Console()

    console.rule(":syringe: vaxup :syringe:")

    with console.status(f"Fetching appointments for {args.date}", spinner="earth"):
        records = get_appointments(args.date)

    entries = []
    failed = False
    for record in records:
        try:
            entry = FormEntry(**record)
            entries.append(entry)
        except ValidationError as e:
            failed = True
            console.print(fmt_err(e, record))
            if args.fix:
                fields = []
                for err in e.errors():
                    name = err["loc"][0]
                    value = Prompt.ask(f"{name}")
                    if value != "":
                        fields.append((name, value))
                if len(fields) > 0:
                    res, fields = edit_appointment(record.get("id"), fields)
                    if res.ok:
                        console.print(
                            "[green bold]Success[/green bold] Updated fields", fields
                        )
                    else:
                        console.print(f"[green bold]Update Failure[/green bold]")
                else:
                    console.print("[bold yellow]Skipped")

    if not failed:
        console.print(f"[bold green]All {len(records)} entries passed validation!")


def enroll(args: argparse.Namespace) -> None:
    console = Console()

    console.rule(":syringe: vaxup :syringe:")
    records = [DUMMY_DATA]  # get_appointments(args.date)

    try:
        entries = [FormEntry(**record) for record in records]
    except ValidationError:
        console.print("[red bold]Error with Acuity data export[/red bold]")
        sys.exit(1)

    username = os.environ.get("VAXUP_USERNAME")
    password = os.environ.get("VAXUP_PASSWORD")

    if not username or not password:
        console.print("Please enter your login")
        username = console.input("[blue]Username[/blue]: ")
        password = console.input("[blue]Password[/blue]: ", password=True)

    if len(records) > 0:
        with console.status("Initialing web-driver..."):
            enroller = AuthorizedEnroller(username, password, args.dry_run)
        enroller.schedule_appointments(entries=entries, console=console)


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    # check
    parser_check = subparsers.add_parser("check")
    parser_check.add_argument("date")
    parser_check.add_argument("--fix", action="store_true")
    parser_check.set_defaults(func=check)

    # enroll
    parser_check = subparsers.add_parser("enroll")
    parser_check.add_argument("date")
    parser_check.add_argument("--dry-run", action="store_true")
    parser_check.set_defaults(func=enroll)

    ns = parser.parse_args(sys.argv[1:])
    ns.func(ns)
