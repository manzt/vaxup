from typing import Iterable

from rich.console import Console
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from vaxup.data import FormEntry, Location, group_entries

URL = "https://vaxmgmt.force.com/authorizedEnroller/s/"
LOGIN_URL = f"{URL}login/"

TIME_STAMP_XPATH = "//c-vcms-book-appointment/article/div[4]/div[2]"


class AuthorizedEnroller:
    def __init__(self, username: str, password: str, test: bool = False):
        self._username = username
        self._password = password
        self._test = test
        self.driver = webdriver.Chrome()

        # Defaults for driver
        self.driver.set_window_position(0, 0)
        self.driver.set_window_size(1024, 700)
        self.driver.implicitly_wait(15)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.driver.close()

    def _find_element(self, xpath: str):
        return self.driver.find_element(By.XPATH, xpath)

    def _login_for(self, location: Location):
        self.driver.get(LOGIN_URL)
        self._find_element("//input[@id='emailAddress-0']").send_keys(self._username)
        self._find_element("//input[@id='loginPassword-0']").send_keys(self._password)
        self._find_element("//lightning-button/button[text()='Log in']").click()
        WebDriverWait(self.driver, 15).until(
            lambda d: d.current_url == URL, "Failed to login."
        )

        self._select_location(location=location)
        WebDriverWait(self.driver, 15).until(
            EC.presence_of_element_located((By.XPATH, TIME_STAMP_XPATH)),
            "Failed to select location.",
        )

    def _select_location(self, location: Location):
        self._find_element(f"//lightning-button[@data-id='{location.value}']").click()

    def _select_date(self, date: str, time: str):
        # Checks if date in middle of page matches our desired date.
        # If not, we need to input a new timestamp and wait until the server
        # responds with new options.
        def date_matches(driver):
            el = driver.find_element(By.XPATH, TIME_STAMP_XPATH)
            return el.text == date

        if not date_matches(self.driver):
            date_picker = self._find_element("//input[@name='scheduleDate']")
            date_picker.clear()
            date_picker.send_keys(date)
            date_picker.send_keys(Keys.RETURN)
            WebDriverWait(self.driver, 10).until(date_matches)

        # Find time slot and click
        # Time must be formatted: HH:MM AM/PM
        self._find_element(f"//lightning-formatted-time[text()='{time}']").click()

    def _click_next(self, first: bool = False):
        path = "//section/button"
        self._find_element(path if first else f"{path}[2]").click()

    def _select_health_screening(self):
        # Click "NO"
        self._find_element("//input[@value='No']/following-sibling::label").click()

    def _fill_personal_information(self, entry: FormEntry):
        def create_finder(xpath_template: str):
            def find_element(value: str):
                xpath = xpath_template.format(value)
                return self._find_element(xpath=xpath)

            return find_element

        find_input = create_finder("//input[@name='{}']")

        # Required
        find_input("firstName").send_keys(entry.first_name)
        find_input("lastName").send_keys(entry.last_name)
        find_input("dateOfBirth").send_keys(entry.dob_str)
        find_input("email").send_keys(entry.email)
        find_input("street").send_keys(entry.street_address)
        find_input("zip").send_keys(entry.zip_code)

        # Need to clear "NYC"
        el = find_input("city")
        el.clear()
        el.send_keys(entry.city)

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
            "//input[@name='races' and @value='{}']/following-sibling::label"
        )
        find_checkbox(entry.race.value).click()

    def _health_insurance(self, has_health_insurance: bool):
        tmp = "//input[@name='{}' and @value='{}']/following-sibling::label"
        if has_health_insurance:
            self._find_element(tmp.format("haveInsurance", "Yes")).click()
            self._find_element(tmp.format("insuranceInformation", "No")).click()
        else:
            self._find_element(tmp.format("haveInsurance", "No")).click()

    def _get_appt_number(self):
        el = self._find_element("//*[contains(text(),'Appointment #')]")
        return el.text.lstrip("Appointment #:")

    def _register(self, entry: FormEntry):
        self.driver.get(URL)

        self._select_date(date=entry.date_str, time=entry.time_str)
        self._click_next(first=True)

        # select elgibility
        self._click_next()

        self._select_health_screening()
        self._click_next()

        self._fill_personal_information(entry=entry)
        self._click_next()

        self._health_insurance(has_health_insurance=entry.has_health_insurance)

        # Submit
        if not self._test:
            self._click_next()
            return self._get_appt_number()

    def schedule_appointments(self, entries: Iterable[FormEntry], console=None):
        console = console if console else Console(quiet=True)
        with console.status("Logging in...", spinner="earth") as status:
            for location, appointments in group_entries(entries=entries):
                status.update(
                    f"[magenta]Logging into {location.name} for {self._username}...",
                    spinner="earth",
                )
                # Need to re-login per location
                self._login_for(location=location)
                status.update(
                    status=f"[yellow]Registering applicant(s) for {location.name}[/yellow]",
                    spinner="bouncingBall",
                    spinner_style="yellow",
                )
                for entry in appointments:
                    try:
                        appt_num = self._register(entry=entry)
                        console.log(
                            f"[green bold]Success[/green bold] - {location.name} {entry.date_str} @ {entry.time_str} - {appt_num}"
                        )
                    except Exception as e:
                        console.log(
                            f"[red bold]Failure[/red bold] - {location.name} {entry.date_str} @ {entry.time_str}"
                        )
                        console.log(e)
