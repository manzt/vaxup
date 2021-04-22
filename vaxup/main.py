from rich.console import Console
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from vaxup.data import FormEntry, FormReader

URL = "https://vaxmgmt.force.com/authorizedEnroller/s/"


def click_next(driver, first=False):
    path = "//section/button"
    driver.find_element(By.XPATH, path if first else f"{path}[2]").click()


def login(driver, username: str, password: str):
    driver.find_element(By.XPATH, "//input[@id='emailAddress-0']").send_keys(username)
    driver.find_element(By.XPATH, "//input[@id='loginPassword-0']").send_keys(password)
    driver.find_element(By.XPATH, "//lightning-button/button").click()


def select_location(driver, entry: FormEntry):
    els = driver.find_elements(By.XPATH, "//lightning-button/button")
    els[entry.location.value].click()


def select_date(driver, entry: FormEntry):
    # TODO: check if current date matches?
    date_picker = driver.find_element(By.XPATH, "//input[@name='scheduleDate']")
    print(entry.date)
    print("TODO, check date: " + date_picker.get_attribute("value"))

    # Find time slot and click
    clicked = False
    for el in driver.find_elements(By.XPATH, "//lightning-formatted-time"):
        if entry.time == el.text:
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


def health_insurance(driver, entry: FormEntry):
    if entry.has_health_insurance:
        # TODO: fill health insurance if available
        driver.find_element(
            By.XPATH, "//input[@value='No']/following-sibling::label"
        ).click()
    else:
        # Click "NO"
        driver.find_element(
            By.XPATH, "//input[@value='No']/following-sibling::label"
        ).click()


def get_appt_number(driver):
    el = driver.find_element(By.XPATH, "//*[contains(text(),'Appointment #')]")
    return el.text.lstrip("Appointment #:")


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
    find_checkbox = create_finder(
        "//li[@class='race_checkbox--li']/span[@data-label='{}']"
    )
    find_checkbox(entry.race.value).click()

    find_dropdown_item = create_finder(
        "//lightning-base-combobox-item[@data-value='{}']"
    )
    # ethnicity
    find_input("ethencity").click()  # open dropdown
    find_dropdown_item(entry.ethnicity.value).click()

    # sex
    find_input("sex").click()  # open dropdown
    find_dropdown_item(entry.sex.value).click()

    # click Next
    click_next(driver)


def run(driver, entry: FormEntry):
    select_date(driver, entry=entry)
    select_elgibility(driver)
    select_health_screening(driver)
    fill_personal_information(driver, entry=entry)
    health_insurance(driver)

    # Submit
    # click_next(driver)

    # return get_appt_number(driver)


def parse_args():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    return parser.parse_args()


def main_():
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

            driver.get(URL)
            driver.implicitly_wait(15)

            login(driver, username=username, password=password)

            # wait until logged in
            WebDriverWait(driver, 15).until(
                lambda d: d.current_url == URL, "Failed to login."
            )

            select_location(driver, location="Church")

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
        driver.close()
        console.log("[red bold]There was an error[/red bold]")
        console.log(e)
