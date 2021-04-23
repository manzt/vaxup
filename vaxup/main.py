from rich.console import Console
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from vaxup.data import FormEntry

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
    print(entry.date_str)
    print("TODO, check date: " + date_picker.get_attribute("value"))

    # Find time slot and click
    for el in driver.find_elements(By.XPATH, "//lightning-formatted-time"):
        if entry.time_str == el.text:
            el.click()
            return

    raise ValueError("Failed to find time.")


def select_health_screening(driver):
    # Click "NO"
    driver.find_element(
        By.XPATH, "//input[@value='No']/following-sibling::label"
    ).click()


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


def fill_personal_information(driver, entry: FormEntry):
    def create_finder(xpath_template: str):
        def find_element(value: str):
            return driver.find_element(By.XPATH, xpath_template.format(value))

        return find_element

    find_input = create_finder("//input[@name='{}']")

    # Required
    find_input("firstName").send_keys(entry.first_name)
    find_input("lastName").send_keys(entry.last_name)
    find_input("dateOfBirth").send_keys(entry.dob_str)
    find_input("email").send_keys(entry.email)
    find_input("street").send_keys(entry.street_address)
    find_input("city").send_key(entry.city)
    find_input("zip").send_keys(entry.zip_code)

    # Optional
    if entry.phone:
        find_input("mobile").send_keys(entry.phone)
    if entry.apt:
        find_input("aptNo").send_keys(entry.apt)

    # Dropdowns. First action opens dropdown, second selects item from list.
    find_dropdown_item = create_finder(
        "//lightning-base-combobox-item[@data-value='{}']"
    )

    find_input("state").click()
    find_dropdown_item(entry.state).click()

    find_input("ethencity").click()
    find_dropdown_item(entry.ethnicity.value).click()

    find_input("sex").click()
    find_dropdown_item(entry.sex.value).click()

    # Race checkbox
    find_checkbox = create_finder(
        "//li[@class='race_checkbox--li']/span[@data-label='{}']"
    )
    find_checkbox(entry.race.value).click()


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


def run(driver, entry: FormEntry):
    select_date(driver, entry=entry)
    click_next(driver, first=True)

    # select elgibility
    click_next(driver)

    select_health_screening(driver)
    click_next(driver)

    fill_personal_information(driver, entry=entry)
    click_next(driver)

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
