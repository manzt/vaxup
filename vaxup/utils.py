import datetime
import os
import sys
from dataclasses import dataclass, asdict
from itertools import groupby
from typing import Iterable, List, Optional, Tuple

from pydantic import ValidationError
from requests.exceptions import HTTPError
from rich import box
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .acuity import (
    AcuityAppointment,
    ErrorNote,
    delete_vax_appointment_id,
    edit_appointment,
    get_appointment,
    get_appointments,
    set_vax_appointment_id,
    set_vax_note,
)
from .data import VaxAppointment
from .web import AuthorizedEnroller

console = Console()


def get_vax_login():
    username = os.environ.get("VAXUP_USERNAME")
    password = os.environ.get("VAXUP_PASSWORD")

    if not username or not password:
        console.print("Please enter your login")
        username = console.input("[blue]Username[/blue]: ")
        password = console.input("[blue]Password[/blue]: ", password=True)

    return username, password


@dataclass
class FieldUpdate:
    name: str
    old: str
    new: str

    def __rich_repr__(self):
        return f"{self.name}: [yellow]{self.old}[/yellow] -> [bold green]{self.new}[/bold green]"


def create_row(appt: AcuityAppointment, issue_fields: Optional[List[str]] = None):
    if issue_fields:
        names = "\n".join(issue_fields)
        values = "\n".join([getattr(appt, n) for n in issue_fields])
    else:
        names, values = "", ""
    row = (
        str(appt.id),
        appt.location.name,
        appt.datetime.strftime("%I:%M %p"),
        names,
        values,
        appt.vax_appointment_id or "",
        "CANCELED" if appt.canceled else "",
        appt.vax_note.value if appt.vax_note else "",
    )
    if not appt.vax_appointment_id and appt.canceled:
        return map(lambda e: "[dim white]" + e, row)
    if appt.vax_appointment_id and appt.canceled:
        return map(lambda e: "[bold yellow]" + e, row)
    return row


def check(date: datetime.date, fix: bool = False) -> None:
    with console.status(f"Fetching appointments for {date}", spinner="earth"):
        appts = get_appointments(date)
        appts += get_appointments(date, canceled=True)

    num_appts = len(appts)

    # no appointments
    if num_appts == 0:
        console.print(f"No appointments scheduled for {date} :calendar:")
        sys.exit(0)

    table = Table(show_header=True, box=box.SIMPLE_HEAD)
    table.add_column("appt. id", style="magenta")
    table.add_column("location")
    table.add_column("time", justify="center")
    table.add_column("field", justify="right", style="yellow")
    table.add_column("value", style="bold yellow")
    table.add_column("vax id", style="bold green", justify="center")
    table.add_column("canceled", justify="center")
    table.add_column("note")

    issues: List[Tuple[AcuityAppointment, List[str]]] = []

    for appt in appts:
        try:
            VaxAppointment.from_acuity(appt)
            table.add_row(*create_row(appt=appt), style="green")
        except ValidationError as e:
            issue_fields = [err["loc"][0] for err in e.errors()]
            table.add_row(*create_row(appt=appt, issue_fields=issue_fields))
            if not appt.canceled:
                # only edit appts that aren't canceled
                issues.append((appt, issue_fields))

    # Just report active appointment numbers
    num_appts = len([apt for apt in appts if not apt.canceled])

    # no errors
    if len(issues) == 0:
        console.print(
            f"[bold green]All {num_appts} active appointments passed validation[/bold green] 🎉"
        )
        console.print(table)
        sys.exit(0)

    # handle errors
    console.print(
        f"[bold yellow]Oops! {len(issues)} of {num_appts} appointments need fixing 🛠️"
    )
    console.print(table)
    if not fix:
        console.print(
            f"Run [yellow]vaxup check {date} --fix[/yellow] to fix interactively."
        )
    else:
        for appt, fields in issues:
            updates: List[FieldUpdate] = []
            for field in fields:
                value = getattr(appt, field)
                update = Prompt.ask(field, default=value, console=console)
                if update != value:
                    updates.append(FieldUpdate(field, value, update))
            text = "\n".join(map(lambda f: f.__rich_repr__(), updates))
            if len(updates) > 0 and Confirm.ask(text, console=console):
                edit_appointment(appt.id, fields={f.name: f.new for f in updates})
            console.print()


def groupby_location(vax_appts: Iterable[VaxAppointment]):
    sorted_appts = sorted(vax_appts, key=lambda e: e.location.value)
    return groupby(sorted_appts, key=lambda e: e.location)


def enroll(date: datetime.date, dry_run: bool = False) -> None:

    with console.status(f"Fetching appointments for {date}", spinner="earth"):
        appts = get_appointments(date)

    if len(appts) == 0:
        console.print(f"No appointments to schedule for {date} :calendar:")
        sys.exit(0)

    try:
        vax_appts = [VaxAppointment.from_acuity(appt) for appt in appts]
    except ValidationError:
        console.print("[red bold]Error with Acuity data export[/red bold]")
        console.print(
            f"Run [yellow]vaxup check {date} --fix[/yellow] to fix interactively"
        )
        sys.exit(1)

    username, password = get_vax_login()

    with console.status("Initialing web-driver...") as status:
        with AuthorizedEnroller(username, password, dry_run) as enroller:
            for location, location_appts in groupby_location(vax_appts=vax_appts):
                status.update(
                    status=f"[yellow]Registering applicant(s) for {location.name}[/yellow]",
                    spinner="bouncingBall",
                    spinner_style="yellow",
                )
                for vax_appt in location_appts:

                    def msg(tag: str, color: str, data=None):
                        line = f"{location.name} {vax_appt.id} {vax_appt.time_str}"
                        line = f"[{color} bold]{tag}[/{color} bold]\t- {line}"
                        return line if not data else line + f" - {data}"

                    if vax_appt.canceled:
                        console.log(
                            msg(
                                "Skipped",
                                "yellow",
                                "Appointment is canceled on Acuity.",
                            )
                        )
                    elif vax_appt.vax_appointment_id:
                        console.log(
                            msg(
                                "Skipped",
                                "yellow",
                                f"Appt #: {vax_appt.vax_appointment_id}",
                            )
                        )
                    elif vax_appt.vax_note is not ErrorNote.NONE:
                        console.log(
                            msg(
                                "Skipped",
                                "yellow",
                                f"[bold yellow]{vax_appt.vax_note.value}",
                            )
                        )
                    else:
                        try:
                            vax_id = enroller.schedule_appointment(appt=vax_appt)
                            console.log(
                                msg(
                                    "Success", "green", f"Appt #: {vax_id or 'DRY_RUN'}"
                                )
                            )
                            if not dry_run:
                                set_vax_appointment_id(
                                    acuity_id=vax_appt.id, vax_appointment_id=vax_id
                                )
                        except HTTPError as e:
                            console.log(
                                f"[yellow bold]WARNING[/yellow bold] failed tag {vax_appt.id} with Appointment #: {vax_id} on Acuity, but VAX registration was sucessful."
                            )
                        except Exception as e:
                            console.log(msg("Failure", "red"))
                            console.log(e)
                            console.print(vax_appt)


def unenroll(acuity_id: int):
    with console.status(f"Fetching appointment for id: {acuity_id}", spinner="earth"):
        appt = get_appointment(acuity_id=acuity_id)
    vax_appt = VaxAppointment.from_acuity(appt)

    if vax_appt.vax_appointment_id is None:
        console.print("[Yellow bold] Oops. No appointment ID found on acuity.")
        sys.exit(1)

    username, password = get_vax_login()

    with console.status("Initialing web-driver...") as status:
        with AuthorizedEnroller(username=username, password=password) as enroller:
            status.update("Cancelling ")
            try:
                enroller.cancel_appointment(appt=vax_appt)
                delete_vax_appointment_id(acuity_id=vax_appt.id)
                console.log(
                    "[bold green]Success![/bold green] cancelled appointment on VAX and removed confirmation number from Acuity"
                )
            except HTTPError as e:
                console.log(
                    f"[yellow bold]WARNING[/yellow bold] Cancelled appointment on VAX but failed to update Acuity."
                )
            except Exception as e:
                console.print(
                    "[bold red]Failure[/bold red] unable to cancel appointment on Vax"
                )
                console.print(e)


def check_id(acuity_id: int, add_note: bool = False):
    with console.status(f"Fetching appointment for id: {acuity_id}", spinner="earth"):
        appt = get_appointment(acuity_id=acuity_id)

    console.print(appt.dict())
    try:
        VaxAppointment.from_acuity(appt)
    except Exception:
        console.print("[yellow bold]Error with some fields...")
        console.print(
            f"Run [yellow]vaxup check {appt.datetime.date().isoformat()} --fix[/yellow] to fix interactively"
        )

    if add_note:
        name = Prompt.ask("Note", choices=[e.name for e in ErrorNote])
        set_vax_note(acuity_id=acuity_id, note=getattr(ErrorNote, name))
