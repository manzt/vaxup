import csv
from dataclasses import dataclass

from selenium import webdriver
from selenium.webdriver.common.by import By

COLUMNS = {
    "Location": "location",
    "Start Time": "start_time",
    # 'Eligibility: Currently only the following groups are eligible to get vaccinated. Check all that apply to you. DO NOT SCHEDULE IF YOU ARE NOT CURRENTLY ELIGIBLE.',
    # '* I hereby certify under penalty of law that I live in New York City or, if I am claiming eligibility based on work or employment status, that I work in New York City. I agree that by selecting 'Yes', my response provided is true and correct.',
    # 'Have you ever had a serious or life-threatening allergic reaction, such as hives or difficulty breathing, to a previous dose of COVID-19 vaccine or any component of the vaccine? IF YES, DO NOT SCHEDULE given you are not eligible to receive the COVID-19.':
    "First Name": "first_name",
    "Last Name": "last_name",
    "Date of birth (M/DD/YYYY)": "dob",
    "Age": "age",
    "Email": "email",
    "Phone": "phone",
    "Street address (e.g., 60 Madison Ave.)": "street_adress",
    "City (e.g., Queens)": "city",
    "State (e.g., NY)": "state",
    "Zip code (e.g., 10010)": "zip_code",
    "Which race do you identify as?": "race",
    "Do you identify as Hispanic, Latino, or Latina?": "identify_as_hispanic_latino_latina",
    "What sex were you assigned at birth?": "sex",
    "Do you have health insurance?": "has_health_insurance",
    # 'Would you like to enter health insurance information now?': '',
    "Type of insurance": "insurance_type",
    "Insurance: Company name": "insurance_company",
    "Insurance: Member ID number": "insurance_number",
}


def ensure_mmddyyyy(date):
    m, d, y = date.split("/")
    return "/".join(
        [
            m if len(m) == 2 else "0" + m,
            d if len(d) == 2 else "0" + d,
            y if len(y) == 4 else "19" + y,
        ]
    )


@dataclass
class FormEntry:
    location: str
    start_time: str
    first_name: str
    last_name: str
    dob: str
    age: int
    email: str
    phone: str
    street_adress: str
    city: str
    state: str
    zip_code: str
    race: str
    identify_as_hispanic_latino_latina: str
    sex: str
    has_health_insurance: str
    insurance_type: str
    insurance_company: str
    insurance_number: str

    @classmethod
    def from_csv_dict(cls, entry):
        fields = {COLUMNS[k]: v for k, v in entry.items() if k in COLUMNS}
        fields["dob"] = ensure_mmddyyyy(fields["dob"])
        return cls(**fields)


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
    with open(args.file, mode="r") as f:
        for row in csv.DictReader(f):
            run(driver, FormEntry.from_csv_dict(row))


if __name__ == "__main__":
    main()
