import datetime
import os
import sys
from itertools import groupby
from typing import Iterable, Union

from pydantic import ValidationError
from requests.exceptions import HTTPError
from rich import box
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .acuity import (
    delete_vax_appointment_id,
    edit_appointment,
    get_appointment,
    get_appointments,
    set_vax_appointment_id,
)
from .data import VaxAppointment, VaxAppointmentError
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


def create_row(record: Union[VaxAppointment, ValidationError]):
    if isinstance(record, VaxAppointmentError):
        names = "\n".join(record.names)
        values = "\n".join(record.values)
    else:
        names, values = "", ""

    cancel_msg = "CANCELED" if record.canceled else ""
    vax_id = record.vax_appointment_id or "[magenta]-------"

    if record.vax_appointment_id is not None and record.canceled:
        cancel_msg = "[yellow bold]" + cancel_msg
        vax_id = "[yellow bold]" + vax_id

    return (
        str(record.id),
        record.location.name,
        record.time_str,
        names,
        values,
        vax_id,
        cancel_msg,
    )


def check(date: datetime.date, fix: bool = False, show_all: bool = False) -> None:
    with console.status(f"Fetching appointments for {date}", spinner="earth"):
        appts = get_appointments(date)
        if show_all:
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
    table.add_column("vax id", style="green")
    table.add_column("canceled", justify="center")

    errors = []
    for appt in appts:
        try:
            vax_appt = VaxAppointment.from_acuity(appt)
            if show_all:
                table.add_row(*create_row(vax_appt), style="green")
        except ValidationError as e:
            err = VaxAppointmentError.from_err(e, appt)
            errors.append(err)
            table.add_row(*create_row(err))

    # no errors
    if len(errors) == 0:
        console.print(f"[bold green]All {num_appts} appointments passed[/bold green] 🎉")
        if show_all:
            console.print(table)
        sys.exit(0)

    # handle errors
    console.print(
        f"[bold yellow]Oops! {len(errors)} of {num_appts} appointments need fixing 🛠️"
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
                edit_appointment(err.id, updates)
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
        sys.exit(1)

    username, password = get_vax_login()

    with console.status("Initialing web-driver...") as status:
        enroller = AuthorizedEnroller(username, password, dry_run)

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
                        msg("Skipped", "yellow", "Appointment is canceled on Acuity.")
                    )
                elif vax_appt.vax_appointment_id is not None:
                    console.log(
                        msg(
                            "Skipped",
                            "yellow",
                            "Appt #: " + vax_appt.vax_appointment_id,
                        )
                    )
                else:
                    try:
                        vax_id = enroller.schedule_appointment(appt=vax_appt)
                        console.log(
                            msg(
                                "Success",
                                "green",
                                vax_id or "DRY_RUN - No VAX Confirmation.",
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
        enroller = AuthorizedEnroller(username, password)
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


def check_id(acuity_id: int, raw: bool = None):
    with console.status(f"Fetching appointment for id: {acuity_id}", spinner="earth"):
        appt = get_appointment(acuity_id=acuity_id)

    if raw:
        console.print(appt.dict())
        console.print(appt.__vaxup__())
    else:
        try:
            vax_appointment = VaxAppointment.from_acuity(appt)
            console.print(f"[bold green]Success 🎉")
            console.print(vax_appointment)
        except Exception as e:
            console.print("[yellow red]Failed")
            console.print(e)
            console.print(appt.__vaxup__())
