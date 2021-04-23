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
        console.log("[bold green]All entries passed validation!")
    else:
        console.log("[bold red]Several errors cannot be resolved.")
        if verbose:
            for err in errors:
                console.log(err)


def main():
    console = Console()
    args = parse_args()

    console.rule(":syringe: vaxup :syringe:")

    reader = AcuityExportReader(getattr(args, "acuity-export"))
    if args.check:
        check(reader=reader, console=console, verbose=args.verbose)
    else:
        console.print("Please enter your login")
        username = console.input("[blue]Username[/blue]: ")
        password = console.input("[blue]Password[/blue]: ", password=True)

        try:
            with console.status(
                "[magenta]Logging into your account...", spinner="earth"
            ) as status:

                console.log("Login sucessful.")

                status.update(
                    status=f"[yellow]Registering applicants...[/yellow]",
                    spinner="bouncingBall",
                    spinner_style="yellow",
                )

                # number = run(driver=driver, entry=entry)
                # console.log(f"Registered: {number}")
                # driver.get(URL)
                # sleep(10)

            # console.print(f"[bold green]Registered {total} applicants successfully")

        except Exception as e:
            console.log("[red bold]There was an error[/red bold]")
            console.log(e)
