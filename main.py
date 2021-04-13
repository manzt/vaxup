import pandas as pd
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


def read(path: str) -> pd.DataFrame:
    if path.endswith(".csv"):
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path)
    return df.rename(columns=COLUMNS)


def elgibility(driver):
    expand = expand_root_element(driver)

    root = expand(driver.find_element(By.TAG_NAME, "c-vcms-schedule-flow"))
    section = expand(
        root.find_element(By.TAG_NAME, "c-vcm-screening-questions-section-a")
    )
    # Question 1
    section.find_element(By.TAG_NAME, "lightning-input").click()

    # Question 2
    yes, no = expand(
        section.find_element(By.TAG_NAME, "lightning-radio-group")
    ).find_elements(By.CSS_SELECTOR, "fieldset > div > span")
    no.click()

    # Question 3
    dob = expand(section.find_elements(By.TAG_NAME, "lightning-input")[1]).find_element(
        By.TAG_NAME, "input"
    )


def parse_args():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    return parser.parse_args()


def expand_root_element(driver):
    return lambda el: driver.execute_script("return arguments[0].shadowRoot", el)


if __name__ == "__main__":
    # args = parse_args()
    driver = webdriver.Chrome()
    driver.get("https://vax4nyc.nyc.gov/patient/s/vaccination-schedule")
    driver.implicitly_wait(15)

    dob = "07/07/1994"
    zip_code = "10001"

    # Question 1: "I affirm that I qualify for one of the following ..."
    driver.find_element(
        By.XPATH,
        '//*[@id="main-content-0"]/div/div[3]/div/div/c-vcms-schedule-flow/main/div[2]/section[1]/div/section/c-vcm-screening-questions-section-a/div/div/div[1]/div/ul/li/span[1]/div/lightning-input/div/span',
    ).click()

    # Question 2: "Are you an employee of the City of New York" (No)
    driver.find_element(
        By.XPATH,
        "/html/body/div[5]/div/div[3]/div/div/c-vcms-schedule-flow/main/div[2]/section[1]/div/section/c-vcm-screening-questions-section-a/div/div/div[2]/div/lightning-radio-group/fieldset/div/span[2]/label",
    ).click()

    # Question 3: DOB
    driver.find_element(
        By.XPATH,
        "/html/body/div[5]/div/div[3]/div/div/c-vcms-schedule-flow/main/div[2]/section[1]/div/section/c-vcm-screening-questions-section-a/div/div/div[3]/lightning-input[1]/lightning-datepicker/div/div/input",
    ).send_keys("07/07/1994")

    # Question 4: Zip Code
    driver.find_element(
        By.XPATH,
        "/html/body/div[5]/div/div[3]/div/div/c-vcms-schedule-flow/main/div[2]/section[1]/div/section/c-vcm-screening-questions-section-a/div/div/div[3]/lightning-input[2]/div/input",
    ).send_keys(zip_code)

    # Question 4: Zip Code
    driver.find_element(
        By.XPATH,
        "/html/body/div[5]/div/div[3]/div/div/c-vcms-schedule-flow/main/div[2]/section[1]/div/section/c-vcm-screening-questions-section-a/div/div/div[3]/lightning-input[2]/div/input",
    ).send_keys(zip_code)

    # Question 5: "I hereby certify under penalty of law that I live in New York City..." (Yes)
    driver.find_element(
        By.XPATH,
        "/html/body/div[5]/div/div[3]/div/div/c-vcms-schedule-flow/main/div[2]/section[1]/div/section/c-vcm-screening-questions-section-a/div/div/div[4]/div/lightning-radio-group/fieldset/div/span[1]/label",
    ).click()
