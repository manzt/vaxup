import csv
from time import sleep

from rich.console import Console

from vaxup.utils import FormEntry


def parse_args():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    return parser.parse_args()


def count_records(filename: str, skip=1):
    with open(filename) as f:
        for i in range(skip):
            next(f)
        total = sum(1 for _ in f)
    return total


def main():
    console = Console()
    args = parse_args()

    console.rule(":syringe: vaxup :syringe:")
    console.print("Please enter your login")
    username = console.input("[blue]Username[/blue]: ")
    password = console.input("[blue]Password[/blue]: ", password=True)
    console.print(f"{username=}, {password=}")

    with console.status(
        "[magenta]Logging into your account...", spinner="earth"
    ) as status:

        sleep(3)
        console.log("Logged in successfully")

        status.update(
            status=f"[yellow]Registering applicants...[/yellow]",
            spinner="bouncingBall",
            spinner_style="yellow",
        )
        total = count_records(args.file)
        with open(args.file) as f:
            for i, row in enumerate(csv.DictReader(f)):

                sleep(0.2)
                entry = FormEntry.from_csv_dict(row)

                if i != 0 and i % 10 == 0:
                    console.log(f"Completed {i} of {total}")

    console.print(f"[bold green]Registered {total} applicants successfully")


if __name__ == "__main__":
    main()
