import datetime
import os
import sys
from dataclasses import dataclass
from itertools import groupby
from typing import Iterable, Optional

from pydantic import ValidationError
from requests.exceptions import HTTPError
from rich import box
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .acuity import AcuityAPI, AcuityAppointment, ErrorNote
from .data import VaxAppointment
from .web import AuthorizedEnroller

console = Console()
api = AcuityAPI()


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

    def __rich__(self):
        return f"{self.name}: [yellow]{self.old}[/yellow] -> [bold green]{self.new}[/bold green]"


class VaxupTable:
    def __init__(self):
        table = Table(show_header=True, box=box.SIMPLE_HEAD)
        table.add_column("appt. id", style="magenta")
        table.add_column("location")
        table.add_column("time", justify="center")
        table.add_column("field", justify="right", style="yellow")
        table.add_column("value", style="bold yellow")
        table.add_column("vax id", style="bold green", justify="center")
        table.add_column("canceled", justify="center")
        table.add_column("note")
        self._table = table

    def add_row(
        self,
        appt: AcuityAppointment,
        issue_fields: Optional[list[str]] = None,
        **kwargs,
    ) -> None:
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
            row = map(lambda e: "[dim white]" + e, row)
        elif appt.vax_appointment_id and appt.canceled:
            row = map(lambda e: "[bold yellow]" + e, row)

        self._table.add_row(*row, **kwargs)

    def __rich__(self):
        return self._table


def check(date: datetime.date, fix: bool = False) -> None:
    with console.status(f"Fetching appointments for {date}", spinner="earth"):
        appts = api.get_appointments(date)
        appts += api.get_appointments(date, canceled=True)

    num_appts = len(appts)

    # no appointments
    if num_appts == 0:
        console.print(f"No appointments scheduled for {date} :calendar:")
        sys.exit(0)

    issues: list[tuple[AcuityAppointment, list[str]]] = []

    table = VaxupTable()
    for appt in appts:
        try:
            VaxAppointment.from_acuity(appt)
            table.add_row(appt, style="green")
        except ValidationError as e:
            issue_fields = [err["loc"][0] for err in e.errors()]
            table.add_row(appt, issue_fields=issue_fields)
            if not appt.canceled:
                # only edit appts that aren't canceled
                issues.append((appt, issue_fields))

    # Just report active appointment numbers
    num_appts = len([apt for apt in appts if not apt.canceled])

    # no errors
    if len(issues) == 0:
        console.print(
            f"[bold green]All {num_appts} active appointments passed validation[/bold green] ????"
        )
        console.print(table)
        sys.exit(0)

    # handle errors
    console.print(
        f"[bold yellow]Oops! {len(issues)} of {num_appts} appointments need fixing ???????"
    )
    console.print(table)
    if not fix:
        console.print(
            f"Run [yellow]vaxup check {date} --fix[/yellow] to fix interactively."
        )
    else:
        for appt, fields in issues:
            updates: list[FieldUpdate] = []
            for field in fields:
                value = getattr(appt, field)
                update = Prompt.ask(field, default=value, console=console)
                if update != value:
                    updates.append(FieldUpdate(field, value, update))
            text = "\n".join(map(lambda f: f.__rich__(), updates))
            if len(updates) > 0 and Confirm.ask(text, console=console):
                api.edit_appointment(appt.id, fields={f.name: f.new for f in updates})
            console.print()


def groupby_location(vax_appts: Iterable[VaxAppointment]):
    sorted_appts = sorted(vax_appts, key=lambda e: e.location.value)
    return groupby(sorted_appts, key=lambda e: e.location)


def enroll(date: datetime.date, dry_run: bool = False) -> None:

    with console.status(f"Fetching appointments for {date}", spinner="earth"):
        appts = api.get_appointments(date)

    if len(appts) == 0:
        console.print(f"No appointments to schedule for {date} :calendar:")
        sys.exit(0)

    try:
        vax_appts = [
            VaxAppointment.from_acuity(appt)
            for appt in appts
            if appt.vax_note is not ErrorNote.INVALID_FORM
        ]

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
                                api.set_vax_id(id=vax_appt.id, vax_id=vax_id)
                        except HTTPError as e:
                            console.log(
                                f"[yellow bold]WARNING[/yellow bold] failed tag {vax_appt.id} with Appointment #: {vax_id} on Acuity, but VAX registration was sucessful."
                            )
                        except Exception as e:
                            console.log(msg("Failure", "red"))
                            console.log(e)
                            console.print(vax_appt)


def unenroll(acuity_id: int) -> None:
    with console.status(f"Fetching appointment for id: {acuity_id}", spinner="earth"):
        appt = api.get_appointment(acuity_id)

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
                api.set_vax_id(id=vax_appt.id, vax_id=None)
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


def check_id(acuity_id: int, add_note: bool = False, raw: bool = False) -> None:
    with console.status(f"Fetching appointment for id: {acuity_id}", spinner="earth"):
        if raw:
            res = api.session.get(api.url(f"/appointments/{acuity_id}"))
            appt = res.json()
        else:
            appt = api.get_appointment(acuity_id)

    console.print(appt)

    if add_note:
        name = Prompt.ask("Note", choices=[e.name for e in ErrorNote])
        api.set_vax_note(id=acuity_id, note=getattr(ErrorNote, name))


def cancel(acuity_id: int):
    cancel_note = None
    notes = None

    if Confirm.ask("Send eligibility message?", console=console):
        cancel_note = """Hello,

Thank you for your interest in scheduling your COVID-19 Vaccination at a Community Healthcare Network Vaccination Site!

Children ages 11 and younger are NOT currently eligible for the COVID-19 (Pfizer) vaccine.

You will be permitted to sign up for an appointment as soon as the CDC eligibility requirements change.


Best,
Charlie
Community Healthcare Network Scheduling Team
"""
        notes = "Not Eligible. Email sent to applicant."

    with console.status(
        f"Canceling appointment on Acuity for id: {acuity_id}", spinner="earth"
    ):
        api.cancel_appointment(id=acuity_id, cancel_note=cancel_note)
        if notes:
            # Tag with internal note if provided.
            api.edit_appointment(id=acuity_id, fields={"notes": notes})
