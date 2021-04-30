from typing import Optional
from time import sleep

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from vaxup.data import Ethnicity, Location, Race, Sex, VaxAppointment

URL = "https://vaxmgmt.force.com/authorizedEnroller/s/"
LOGIN_URL = f"{URL}login/"
CHANGE_APPOINTMENT_URL = f"{URL}change-existing-appointment"
TIME_STAMP_XPATH = "//c-vcms-book-appointment/article/div[4]/div[2]"


# Values are the "data-id" attribute for the "Select" buttons after login on website.
# e.g. <lightning-button data-id='0013d000002jkZPAAY'>
LOCATION = {
    Location.EAST_NY: "0013d000002jkZPAAY",
    Location.HARLEM: "0013d000002jkZ0AAI",
    Location.WASHINGTON_HEIGHTS: "0013d000002vZH6AAM",
    Location.SOUTH_JAMAICA: "0013d000002jkSKAAY",
}

# Values are the "data-label" attribute for the clickable span on website.
# e.g. <span data-label='Other'...>
RACE = {
    Race.BLACK: "Black, including African American or Afro-Caribbean",
    Race.ASIAN: "Asian, including South Asian",
    Race.NATIVE_AMERICAN: "Native American or Alaska Native",
    Race.PACIFIC_ISLANDER: "Native Hawaiian or Pacific Islander",
    Race.WHITE: "White",
    Race.PREFER_NOT_TO_ANSWER: "Prefer not to answer",
    Race.OTHER: "Other",
}

# Values are the "data-value" attribute for the dropdown on website.
# e.g. <lightning-base-combobox-item data-value='Unknown' ...>
SEX = {
    Sex.MALE: "Male",
    Sex.FEMALE: "Female",
    Sex.NEITHER: "Neither male or female",
    Sex.UNKNOWN: "Unknown",
}

# Values are the "data-value" attribute for the dropdown on website.
# e.g. <lightning-base-combobox-item data-value='Prefer not to answer' ... >
ETHNICITY = {
    Ethnicity.LATINX: "Yes, Hispanic, Latino, or Latina",
    Ethnicity.NOT_LATINX: "No, not Hispanic, Latino, or Latina",
    Ethnicity.PERFER_NOT_TO_ANSWER: "Prefer not to answer",
}


class AuthorizedEnroller:
    _username: str
    _password: str
    _test: bool
    _current_location: Optional[Location]
    driver: webdriver.Chrome

    def __init__(
        self,
        username: str,
        password: str,
        test: bool = False,
    ):
        self._username = username
        self._password = password
        self._test = test
        self._current_location = None
        self.driver = webdriver.Chrome()

        # Defaults for driver
        self.driver.set_window_position(0, 0)
        self.driver.set_window_size(1024, 700)
        self.driver.implicitly_wait(5)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.driver.close()

    def _find_element(self, xpath: str) -> WebElement:
        return self.driver.find_element(By.XPATH, xpath)

    def _select_location(self, location: Location) -> None:
        data_id = LOCATION[location]
        self._find_element(f"//lightning-button[@data-id='{data_id}']").click()

    def _select_date(self, date: str, time: str) -> None:
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
            sleep(1)

        # Find time slot and click
        # Time must be formatted: HH:MM AM/PM
        self._find_element(f"//lightning-formatted-time[text()='{time}']").click()

    def _click_next(self, first: bool = False) -> None:
        path = "//section/button"
        self._find_element(path if first else f"{path}[2]").click()

    def _select_health_screening(self) -> None:
        # Click "NO"
        self._find_element("//input[@value='No']/following-sibling::label").click()

    def _fill_personal_information(self, appt: VaxAppointment) -> None:
        def create_finder(xpath_template: str):
            def find_element(value: str):
                xpath = xpath_template.format(value)
                return self._find_element(xpath=xpath)

            return find_element

        find_input = create_finder("//input[@name='{}']")

        # Required
        find_input("firstName").send_keys(appt.first_name)
        find_input("lastName").send_keys(appt.last_name)
        find_input("dateOfBirth").send_keys(appt.dob_str)
        find_input("email").send_keys(appt.email)
        find_input("street").send_keys(appt.street_address)
        find_input("zip").send_keys(appt.zip_code)

        # Need to clear "NYC"
        el = find_input("city")
        el.clear()
        el.send_keys(appt.city)

        # Optional
        if appt.phone:
            find_input("mobile").send_keys(appt.phone)
        if appt.apt:
            find_input("aptNo").send_keys(appt.apt)

        # Dropdowns. First action opens dropdown, second selects item from list.
        find_dropdown_item = create_finder(
            "//lightning-base-combobox-item[@data-value='{}']"
        )

        find_input("state").click()
        find_dropdown_item(appt.state).click()

        find_input("ethencity").click()
        find_dropdown_item(ETHNICITY[appt.ethnicity]).click()

        find_input("sex").click()
        find_dropdown_item(SEX[appt.sex]).click()

        # Race checkbox
        find_checkbox = create_finder(
            "//input[@name='races' and @value='{}']/following-sibling::label"
        )
        find_checkbox(RACE[appt.race]).click()

    def _health_insurance(self, has_health_insurance: bool) -> None:
        tmp = "//input[@name='{}' and @value='{}']/following-sibling::label"
        if has_health_insurance:
            self._find_element(tmp.format("haveInsurance", "Yes")).click()
            self._find_element(tmp.format("insuranceInformation", "No")).click()
        else:
            self._find_element(tmp.format("haveInsurance", "No")).click()

    def _get_appt_id(self) -> str:
        el = self._find_element("//*[contains(text(),'Appointment #')]")
        return el.text.lstrip("Appointment #:")

    # Explicit login to location
    def login(self, location: Location):
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
        self._current_location = location

    def schedule_appointment(self, appt: VaxAppointment):
        if appt.vax_appointment_id is not None:
            raise ValueError("Appointment already registered on VAX.")

        # implicit login if current location doesn't match
        if appt.location != self._current_location:
            self.login(location=appt.location)
        else:
            self.driver.get(URL)
        self._select_date(date=appt.date_str, time=appt.time_str)
        self._click_next(first=True)

        # select elgibility
        self._click_next()

        self._select_health_screening()
        self._click_next()

        self._fill_personal_information(appt=appt)
        self._click_next()

        self._health_insurance(has_health_insurance=appt.has_health_insurance)

        # Submit
        if not self._test:
            self._click_next()
            return self._get_appt_id()

    def cancel_appointment(self, appt: VaxAppointment):
        if appt.vax_appointment_id is None:
            raise ValueError("No VAX Appointment Number.")

        if appt.location != self._current_location:
            self.login(location=appt.location)

        self.driver.get(CHANGE_APPOINTMENT_URL)
        self._find_element(
            "//lightning-input[@data-id='appointmentIdField']"
        ).send_keys(appt.vax_appointment_id)
        self._find_element("//lightning-button/button[text() = 'Search']").click()
        self._find_element("//button[@name='cancel' and @data-index='0']").click()
        self._find_element("//button[text() = 'Yes']").click()
