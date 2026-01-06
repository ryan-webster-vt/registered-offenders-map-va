import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote_plus
import time
import re
import random

TIMEOUT = 15
CHROMEDRIVER_PATH = r"C:\Users\ljrwe\OneDrive\Desktop\registered-offenders-map-va\chromedriver.exe"

def build_county_url(county):
    encoded = quote_plus(county)
    return f'https://www.vspsor.com/Search/Results?Filter=None&firstName=&lastName=&registrationNumber=&Address=&County={encoded}&Zip='

def wait_for_table_text(driver, timeout=20):
    WebDriverWait(driver, timeout).until(
        lambda d: "of" in d.find_element(By.ID, "offenderTable_info").text.lower()
        or "no matching" in d.find_element(By.ID, "offenderTable_info").text.lower()
    )


def scrape_offender_count(driver, url, retries=5):
    for attempt in range(1, retries + 1):
        try:
            driver.get(url)
            wait_for_table_text(driver)

            info_div = driver.find_element(By.ID, "offenderTable_info")
            text = info_div.text.strip().lower()

            print(f"INFO TEXT: {text}")

            # Handle zero cases explicitly
            if "no matching" in text or "of 0" in text:
                print(f"Success: 0 -> {url}")
                return 0

            match = re.search(r'of\s+([\d,]+)', text)
            if match:
                count = int(match.group(1).replace(",", ""))
                print(f"Success: {count} -> {url}")
                return count

            # If text exists but no count yet, force retry
            raise ValueError("Count not yet available")

        except Exception as e:
            print(f"[Retry {attempt}] {url} failed: {e}")
            time.sleep(random.uniform(3, 6))

    print(f"[FAILED] {url}")
    return None



def main():
    pop_df = pd.read_csv('data/total_population.csv')
    
    # Set up Selenium Chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(
    service=Service(CHROMEDRIVER_PATH),
    options=chrome_options
)
    
    results = []
    
    for county in pop_df['locality']:
        time.sleep(random.uniform(2.5, 4.5))
        url = build_county_url(county)
        offender_count = scrape_offender_count(driver, url)
        print(f'{county} successfully scraped')
        print(offender_count)
        population = pop_df.loc[pop_df['locality'] == county, 'population'].values[0]
        per_capita = offender_count / population if offender_count and population else None
        
        results.append({
            "county": county,
            "population": population,
            "offender_count": offender_count,
            "per_capita": per_capita
        })
    
    driver.quit()
    
    result_df = pd.DataFrame(results)
    result_df.to_csv('data/offender_population.csv', index=False)

if __name__ == '__main__':
    main()
    