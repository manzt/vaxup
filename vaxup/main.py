import csv
import getpass

from selenium import webdriver
from selenium.webdriver.common.by import By

from vaxup.utils import FormEntry


def login(driver):
    username = input("Username: ")
    password = getpass.getpass()
    print(f"{username=}, {password=}")
    # TODO: perform login
    # driver.get()


def run(driver, entry: FormEntry):
    driver.get("https://vax4nyc.nyc.gov/patient/s/vaccination-schedule")
    driver.implicitly_wait(15)

    # CSS / TAG selectors don't work because elements are web-components and
    # hidden due to shadow DOM. For some reason XPATH selectors _do_ work...

    # Question 1: "I affirm that I qualify for one of the following ..."
    driver.find_element(By.XPATH, "//label[@for='checkbox-11']").click()
    # Question 2: "Are you an employee of the City of New York" (No)
    driver.find_element(By.XPATH, "//label[@for='radio-1-4']").click()
    # Question 3: DOB
    driver.find_element(By.XPATH, "//input[@id='input-6']").send_keys(entry.dob)
    # Question 4: Zip Code
    driver.find_element(By.XPATH, "//input[@id='input-9']").send_keys(entry.zip_code)
    # Question 5: "I hereby certify under penalty of law that I live in New York City..." (Yes)
    driver.find_element(By.XPATH, "//label[@for='radio-0-10']").click()


def parse_args():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    return parser.parse_args()


def main():
    args = parse_args()
    driver = webdriver.Chrome()
    login(driver)
    with open(args.file, mode="r") as f:
        for row in csv.DictReader(f):
            entry = FormEntry.from_csv_dict(row)
            run(driver, entry)
    driver.close()


if __name__ == "__main__":
    main()
