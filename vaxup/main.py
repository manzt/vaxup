import csv
from time import sleep

from rich.console import Console
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


from vaxup.utils import FormEntry, ensure_mmddyyyy

URL = "https://vaxmgmt.force.com/authorizedEnroller/s/"


def click_next(driver, first=False):
    path = "//section/button"
    driver.find_element(By.XPATH, path if first else f"{path}[2]").click()


def login(driver, username: str, password: str):
    driver.find_element(By.XPATH, "//input[@id='emailAddress-0']").send_keys(username)
    driver.find_element(By.XPATH, "//input[@id='loginPassword-0']").send_keys(password)
    driver.find_element(By.XPATH, "//lightning-button/button").click()


def select_location(driver, location: str):
    # map unique location string to element on screen
    els = driver.find_elements(By.XPATH, "//lightning-button/button")
    for name, el in zip(("Church", "Convent", "Washington", "Jerusalem"), els):
        if name in location:
            el.click()
            return


def select_date(driver, entry: FormEntry):
    date, time = entry.start_time.split(" ")
    date = ensure_mmddyyyy(date)

    # TODO: check if current date matches?
    date_picker = driver.find_element(By.XPATH, "//input[@id='input-12']")

    # Find time slot and click
    clicked = False
    for el in driver.find_elements(By.XPATH, "//lightning-formatted-time"):
        # time in HH:MM AM/PM format
        t, meridiem = el.text.split(" ")
        t = t.lstrip("0")  # remove leading "0" if present
        if time.upper() == (t + meridiem):
            el.click()
            clicked = True

    if not clicked:
        raise ValueError("Failed to find time.")

    # Click Next
    click_next(driver, first=True)


def select_elgibility(driver):
    click_next(driver)


def select_health_screening(driver):
    # Click "NO"
    driver.find_element(
        By.XPATH, "//input[@value='No']/following-sibling::label"
    ).click()
    # Click Next
    click_next(driver)


def fill_personal_information(driver, entry: FormEntry):
    def create_finder(xpath_template: str):
        def find_element(value: str):
            return driver.find_element(By.XPATH, xpath_template.format(value))

        return find_element

    find_input = create_finder("//input[@name='{}']")

    find_input("firstName").send_keys(entry.first_name)
    find_input("lastName").send_keys(entry.last_name)
    find_input("dateOfBirth").send_keys(entry.dob)
    find_input("email").send_keys(entry.email)
    find_input("mobile").send_keys(entry.phone)
    find_input("street").send_keys(entry.street_address)
    find_input("zip").send_keys(entry.zip_code)

    # race checkbox
    race = entry.race.lower()
    find_checkbox = create_finder(
        "//li[@class='race_checkbox--li']/span[@data-label='{}']"
    )
    if "asian" in race:
        data_label = "Asian, including South Asian"
    elif "black" in race:
        data_label = "Black, including African American or Afro-Caribbean"
    elif "alaska" in race:
        data_label = "Native American or Alaska Native"
    elif "pacific" in race:
        data_label = "Native Hawaiian or Pacific Islander"
    elif "white" in race:
        data_label = "White"
    elif "prefer" in race:
        data_label = "Prefer not to answer"
    else:
        data_label = "Other"
    find_checkbox(data_label).click()

    find_dropdown_item = create_finder(
        "//lightning-base-combobox-item[@data-value='{}']"
    )
    # ethnicity
    find_input("ethencity").click()  # open dropdown
    answer = entry.identify_as_hispanic_latino_latina.lower().strip()
    if "yes" == answer:
        data_value = "Yes, Hispanic, Latino, or Latina"
    elif "no" == answer:
        data_value = "No, not Hispanic, Latino, or Latina"
    else:
        data_value = "Prefer not to answer"
    find_dropdown_item(data_value).click()

    # sex
    find_input("sex").click()  # open dropdown
    answer = entry.sex.lower()
    if "male" == answer:
        data_value = "Male"
    elif "female" == answer:
        data_value = "Female"
    elif "neither" in answer:
        data_value = "Neither male or female"
    else:
        data_value = "Unknown"
    find_dropdown_item(data_value).click()

    # click Next
    click_next(driver)


def health_insurance(driver):
    # TODO: fill health insurance if available
    # Click "NO"
    driver.find_element(
        By.XPATH, "//input[@value='No']/following-sibling::label"
    ).click()


def run(driver, username: str, password: str, entry: FormEntry):
    driver.get(URL)
    driver.implicitly_wait(15)

    login(driver, username=username, password=password)

    # wait until logged in
    WebDriverWait(driver, 15).until(lambda d: d.current_url == URL, "Failed to login.")

    select_location(driver, location=entry.location)
    select_date(driver, entry=entry)
    select_elgibility(driver)
    select_health_screening(driver)
    fill_personal_information(driver, entry=entry)
    health_insurance(driver)

    # TODO: Submit


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

    driver = webdriver.Chrome()
    driver.set_window_position(0, 0)
    driver.set_window_size(1024, 700)

    try:
        with console.status(
            "[magenta]Logging into your account...", spinner="earth"
        ) as status:

            console.log("Logged in successfully")

            status.update(
                status=f"[yellow]Registering applicants...[/yellow]",
                spinner="bouncingBall",
                spinner_style="yellow",
            )

            with open(args.file) as f:
                data = next(csv.DictReader(f))
                entry = FormEntry.from_csv_dict(data)
                #         if i != 0 and i % 10 == 0:
                #             console.log(f"Completed {i} of {total}")

                run(driver, username=username, password=password, entry=entry)
                sleep(3)

        # console.print(f"[bold green]Registered {total} applicants successfully")

    except Exception as e:
        driver.close()
        console.log("[red bold]There was an error[/red bold]")
        console.log(e)
