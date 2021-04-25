import argparse
import datetime
import os
import sys

from pydantic import ValidationError
from rich.console import Console

from vaxup.data import AcuityExportReader, FormEntry
from vaxup.web import AuthorizedEnroller


def parse_args():

    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def fmt_err(e, record):
    fields = []
    for err in e.errors():
        field = err["loc"][0]
        fields.append({field: record[field]})
    date = datetime.datetime.strptime(record["start_time"], "%Y-%m-%dT%H:%M:%S%z")
    date = date.strftime("%Y-%m-%d @ %I:%M %p")
    return f"[red bold]Error[/red bold] - id={record.get('id')} {date=} {fields=}"


def check(reader: AcuityExportReader, console: Console, verbose: bool):
    entries = []
    errors = []
    for record in reader:
        try:
            entry = FormEntry(**record)
            entries.append(entry)
        except ValidationError as e:
            # errors.append(e)
            errors.append(fmt_err(e, record))

    if len(errors) == 0:
        console.print(f"[bold green]All {len(reader)} entries passed validation!")
    else:
        console.print(
            f"[bold yellow]Form errors in {len(errors)} of {len(reader)} entries."
        )
        if verbose:
            for err in errors:
                # console.print(err.json())
                console.print(err)


def main():
    console = Console()
    args = parse_args()

    console.rule(":syringe: vaxup :syringe:")

    reader = AcuityExportReader(args.file)

    if args.check:
        check(reader=reader, console=console, verbose=args.verbose)
        sys.exit(0)

    try:
        entries = [FormEntry(**record) for record in reader]
    except ValidationError:
        console.print("[red bold]Error with Acuity data export[/red bold]")
        console.print(
            f" Run [yellow bold]vaxup {args.file} --check[/yellow bold] for help"
        )
        sys.exit(1)

    username = os.environ.get("VAXUP_USERNAME")
    password = os.environ.get("VAXUP_PASSWORD")

    if not username or not password:
        console.print("Please enter your login")
        username = console.input("[blue]Username[/blue]: ")
        password = console.input("[blue]Password[/blue]: ", password=True)

    with console.status("Initialing web-driver..."):
        enroller = AuthorizedEnroller(username, password, args.dry_run)
    enroller.schedule_appointments(entries=entries, console=console)
