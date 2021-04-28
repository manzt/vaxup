import os
import datetime
import sys

from pydantic import ValidationError
from rich import box
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .acuity import get_appointments
from .data import FormEntry, FormError
from .web import AuthorizedEnroller
from .console import console


def check(date: datetime.date, fix: bool = False, show_all: bool = False) -> None:
    with console.status(f"Fetching appointments for {date}", spinner="earth"):
        records = get_appointments(date)

    # no appointments
    if len(records) == 0:
        console.print(f"No appointments scheduled for {date} :calendar:")
        sys.exit(0)

    table = Table(
        show_header=True,
        row_styles=None if show_all else ["none", "dim"],
        box=box.SIMPLE_HEAD,
    )
    table.add_column("appt. id", style="magenta")
    table.add_column("time", justify="center")
    table.add_column("field", justify="right", style="yellow")
    table.add_column("value", style="bold yellow")

    errors = []
    for record in records:
        try:
            entry = FormEntry(**record)
            if show_all:
                table.add_row(str(entry.id), entry.time_str, "", "", style="green")
        except ValidationError as e:
            err = FormError.from_err(e, record)
            errors.append(err)
            table.add_row(
                str(err.id), err.time, "\n".join(err.names), "\n".join(err.values)
            )

    # no errors
    if len(errors) == 0:
        console.print(
            f"[bold green]All {len(records)} appointments passed[/bold green] 🎉"
        )
        if show_all:
            console.print(table)
        sys.exit(0)

    # handle errors
    console.print(
        f"[bold yellow]Oops! {len(errors)} of {len(records)} appointments need fixing 🛠️"
    )
    console.print(table)
    if not fix:
        console.print(
            f"Run [yellow]vaxup check {date} --fix[/yellow] to fix interactively."
        )
    else:
        for err in errors:
            updates = []
            for name, value in err.fields:
                update = Prompt.ask(name, default=value, console=console)
                if update != value:
                    updates.append((name, value, update))

            text = "\n".join(
                [
                    f"{n}: [yellow]{v}[/yellow] -> [bold green]{u}[/bold green]"
                    for n, v, u in updates
                ]
            )
            if len(updates) > 0 and Confirm.ask(text, console=console):
                updates = [(n, u) for n, _, u in updates]
                # TODO
                # res = edit_appointment(err.id, updates)
                # console.print(res)
            console.print()


def enroll(date: datetime.date, dry_run: bool = False) -> None:
    from .data import DUMMY_DATA

    records = [DUMMY_DATA]  # get_appointments(date)

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
            enroller = AuthorizedEnroller(username, password, dry_run)
        enroller.schedule_appointments(entries=entries)
