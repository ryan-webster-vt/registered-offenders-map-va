import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from urllib.parse import quote_plus
import time
import re
import random

TIMEOUT = 15
CHROMEDRIVER_PATH = r"C:\Users\ljrwe\OneDrive\Desktop\registered-offenders-map-va\chromedriver.exe"

def build_county_url(county):
    encoded = quote_plus(county)
    url_none = f'https://www.vspsor.com/Search/Results?Filter=None&firstName=&lastName=&registrationNumber=&Address=&County={encoded}&Zip='
    url_homeless = f'https://www.vspsor.com/Search/Results?Filter=Homeless&firstName=&lastName=&registrationNumber=&Address=&County={encoded}&Zip='
    url_not_incarcerated = f'https://www.vspsor.com/Search/Results?Filter=NotIncarcerated&firstName=&lastName=&registrationNumber=&Address=&County={encoded}&Zip='
    url_civilly_comitted = f'https://www.vspsor.com/Search/Results?Filter=CivillyCommitted&firstName=&lastName=&registrationNumber=&Address=&County={encoded}&Zip='
    url_incarcerated = f'https://www.vspsor.com/Search/Results?Filter=Incarcerated&firstName=&lastName=&registrationNumber=&Address=&County={encoded}&Zip='
    url_list = [url_none, url_homeless, url_not_incarcerated, url_civilly_comitted, url_incarcerated]
    return url_list

def wait_for_table_text(driver, timeout=20):
    WebDriverWait(driver, timeout).until(
        lambda d: "of" in d.find_element(By.ID, "offenderTable_info").text.lower()
        or "no matching" in d.find_element(By.ID, "offenderTable_info").text.lower()
    )


def scrape_offender_count(driver, url_list, retries=5):
    count_list = []
    for url in url_list:
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
                    count_list.append(0)
                    break

                match = re.search(r'of\s+([\d,]+)', text)
                if match:
                    count = int(match.group(1).replace(",", ""))
                    print(f"Success: {count} -> {url}")
                    count_list.append(count)
                    break

                # If text exists but no count yet, force retry
                raise ValueError("Count not yet available")

            except Exception as e:
                print(f"[Retry {attempt}] {url} failed: {e}")
                time.sleep(random.uniform(3, 6))
            print(f"[FAILED] {url}")
    return count_list



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
    
    for i, county in enumerate(pop_df['locality']):
        print(f"{i+1} / {len(pop_df['locality'])}")
        time.sleep(random.uniform(2.5, 4.5))

        url_list = build_county_url(county)
        offender_count_list = scrape_offender_count(driver, url_list)

        print(f'{county} successfully scraped')
        print(offender_count_list)
        
        population = pop_df.loc[pop_df['locality'] == county, 'population'].values[0]

        total_offender_count = offender_count_list[0]
        total_offender_count_homeless = offender_count_list[1]
        total_offender_count_non_incarcerated = offender_count_list[2]
        total_offender_count_civilly_comitted = offender_count_list[3]
        total_offender_count_incarcerated = offender_count_list[4]

        per_capita_all = total_offender_count / population
        per_capita_homeless = total_offender_count_homeless / population
        per_capita_non_incarcerated = total_offender_count_non_incarcerated / population
        per_capita_civilly_comitted = total_offender_count_civilly_comitted / population
        per_capita_incarcerated = total_offender_count_incarcerated / population

        results.append({
            "county": county,
            "population": population,
            "total_offender_count": total_offender_count,
            'total_offender_count_homeless' : total_offender_count_homeless,
            'total_offender_count_non_incarcerated' : total_offender_count_non_incarcerated,
            'total_offender_count_civilly_comitted' : total_offender_count_civilly_comitted,
            'total_offender_count_incarcerated' : total_offender_count_incarcerated,
            "per_capita_all": per_capita_all,
            'per_capita_homeless' : per_capita_homeless,
            'per_capita_non_incarcerated' : per_capita_non_incarcerated,
            'per_capita_civilly_comitted' : per_capita_civilly_comitted,
            'per_capita_incarcerated' : per_capita_incarcerated
        })
    
    driver.quit()
    
    result_df = pd.DataFrame(results)
    result_df.to_csv('data/offender_population.csv', index=False)

if __name__ == '__main__':
    main()
    