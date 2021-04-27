import argparse
import os
import sys

from pydantic import ValidationError
from rich import box
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from vaxup.acuity import edit_appointment, get_appointments
from vaxup.data import DUMMY_DATA, FormEntry, FormError
from vaxup.web import AuthorizedEnroller


def check(args: argparse.Namespace) -> None:
    console = Console()

    with console.status(f"Fetching appointments for {args.date}", spinner="earth"):
        records = get_appointments(args.date)

    if len(records) == 0:
        console.print(f"No appointments scheduled for {args.date} :calendar:")
        sys.exit(0)

    table = Table(show_header=True, row_styles=["none", "dim"], box=box.SIMPLE_HEAD)
    table.add_column("appt. id", style="magenta")
    table.add_column("date", justify="center")
    table.add_column("time", justify="center")
    table.add_column("field", justify="right", style="yellow")
    table.add_column("value", style="bold yellow")

    errors = []
    for record in records:
        try:
            FormEntry(**record)
        except ValidationError as e:
            err = FormError.from_err(e, record)
            errors.append(err)
            table.add_row(
                str(err.id),
                err.date,
                err.time,
                "\n".join(err.names),
                "\n".join(err.values),
            )

    if len(errors) > 0:
        console.print(
            f"[bold yellow]Oops! {len(errors)} of {len(records)} appointments need fixing 🛠️"
        )
        console.print(table)
        if not args.fix:
            console.print(
                f"Run [yellow]vaxup check {args.date} --fix[/yellow] to fix interactively."
            )
        else:
            console.print("[bold red]WIP, fix not implemented...")
    else:
        console.print(
            f"[bold green]All {len(records)} appointments passed[/bold green] 🎉"
        )


def enroll(args: argparse.Namespace) -> None:
    console = Console()
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
