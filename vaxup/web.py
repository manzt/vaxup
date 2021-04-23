from typing import List
from itertools import groupby

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from vaxup.data import FormEntry, Location

URL = "https://vaxmgmt.force.com/authorizedEnroller/s/"
LOGIN_URL = f"{URL}login/"


class AuthorizedEnroller:
    def __init__(self, username: str, password: str):
        self._username = username
        self._password = password
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

    def _login(self):
        self.driver.get(LOGIN_URL)
        self._find_element("//input[@id='emailAddress-0']").send_keys(self._username)
        self._find_element("//input[@id='loginPassword-0']").send_keys(self._password)
        self._find_element("//lightning-button/button[text()='Log in']").click()
        WebDriverWait(self.driver, 15).until(
            lambda d: d.current_url == URL, "Failed to login."
        )

    def _select_location(self, location: Location):
        self._find_element(f"//lightning-button[@data-id='{location.value}']").click()

    def _select_date(self, date: str, time: str):
        # TODO: check if current date matches?
        date_picker = self._find_element("//input[@name='scheduleDate']")
        print(date)
        print("TODO, check date: " + date_picker.get_attribute("value"))

        # Find time slot and click
        for el in self.driver.find_elements(By.XPATH, "//lightning-formatted-time"):
            if time == el.text:
                el.click()
                return

        raise ValueError("Failed to find time.")

    def _click_next(self, first=False):
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

    def _health_insurance(self, has_health_insurance: bool):
        if has_health_insurance:
            # TODO: fill health insurance if available
            self._find_element("//input[@value='No']/following-sibling::label").click()
        else:
            # Click "NO"
            self._find_element("//input[@value='No']/following-sibling::label").click()

    def _get_appt_number(self):
        el = self._find_element("//*[contains(text(),'Appointment #')]")
        return el.text.lstrip("Appointment #:")

    def _register(self, entry: FormEntry):
        self._select_date(date=entry.date_str, time=entry.time_str)
        self._click_next(first=True)

        # select elgibility
        self._click_next()

        self._select_health_screening()
        self._click_next()

        self._fill_personal_information(entry=entry)
        self._click_next()

        self._health_insurance()

        # Submit
        # click_next(driver)

        # return get_appt_number(driver)

    def schedule_appointments(self, entries: List[FormEntry]):
        sorted_entries = sorted(entries, key=lambda e: e.location.value)
        for location, appts in groupby(sorted_entries, key=lambda e: e.location):
            self._login(location=location)
            for appt in appts:
                print(appt)
