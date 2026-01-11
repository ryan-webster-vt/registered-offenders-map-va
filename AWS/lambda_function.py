import pandas as pd
import boto3
import time
import re
import random

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options as ChromeOptions

from tempfile import mkdtemp

from urllib.parse import quote_plus

from io import BytesIO

from datetime import date


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
                time.sleep(0.5)
            print(f"[FAILED] {url}")
    return count_list


def handler(event, context):
    # Read locality population data from S3
    s3 = boto3.client('s3')
    bucket_name = 'registered-offender-bucket'
    file_key = 'total_population.csv'
    obj = s3.get_object(Bucket=bucket_name, Key=file_key)

    population_df = pd.read_csv(obj['Body'])

    # Initialize Chrome driver
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-tools")
    chrome_options.add_argument("--no-zygote")
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument(f"--user-data-dir={mkdtemp()}")
    chrome_options.add_argument(f"--data-path={mkdtemp()}")
    chrome_options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    chrome_options.add_argument("--remote-debugging-pipe")
    chrome_options.add_argument("--verbose")
    chrome_options.add_argument("--log-path=/tmp")
    chrome_options.binary_location = "/opt/chrome/chrome-linux64/chrome"

    service = Service(
        executable_path="/opt/chrome-driver/chromedriver-linux64/chromedriver",
        service_log_path="/tmp/chromedriver.log"
    )

    driver = webdriver.Chrome(
        service=service,
        options=chrome_options
    )

    results = []
    
    for i, county in enumerate(population_df['locality']):
        print(f"{i+1} / {len(population_df['locality'])}")
        time.sleep(0.25)

        url_list = build_county_url(county)
        offender_count_list = scrape_offender_count(driver, url_list)

        print(f'{county} successfully scraped')
        print(offender_count_list)
        
        population = population_df.loc[population_df['locality'] == county, 'population'].values[0]

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

    # Convert DataFrame to CSV string
    xlsx_buffer = BytesIO()
    result_df.to_excel(xlsx_buffer, index=False)

    # Upload to S3
    s3 = boto3.client('s3')
    today = date.today()
    s3.put_object(Bucket=bucket_name, Key=f'offender_population_{today}.xlsx', Body=xlsx_buffer.getvalue())

    return 'Success!!!'
