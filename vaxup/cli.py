from vaxup.web import AuthorizedEnroller
from pydantic import ValidationError
from rich.console import Console

from vaxup.data import AcuityExportReader, FormEntry, FormError


def parse_args():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("acuity-export")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def check(reader: AcuityExportReader, console: Console, verbose: bool):
    entries = []
    errors = []
    for record in reader:
        try:
            entry = FormEntry(**record)
            entries.append(entry)
        except ValidationError as e:
            errors.append(FormError.from_err(e, record))

    if len(errors) == 0:
        console.print("[bold green]All entries passed validation!")
    else:
        console.print(f"[bold yellow]Form errors in {len(errors)} of {1} entries.")
        if verbose:
            for err in errors:
                console.print(err)


def main():
    console = Console()
    args = parse_args()

    console.rule(":syringe: vaxup :syringe:")

    reader = AcuityExportReader(getattr(args, "acuity-export"))
    if args.check:
        check(reader=reader, console=console, verbose=args.verbose)
    else:
        entries = [FormEntry(**record) for record in reader]

        console.print("Please enter your login")
        username = console.input("[blue]Username[/blue]: ")
        password = console.input("[blue]Password[/blue]: ", password=True)

        try:
            with console.status("Initialing web-driver...") as status:
                enroller = AuthorizedEnroller(username, password)
                enroller.schedule_appointments(entries=entries, status=status)
            # console.print(f"[bold green]Registered {total} applicants successfully")

        except Exception as e:
            console.log("[red bold]There was an error[/red bold]")
            console.log(e)
