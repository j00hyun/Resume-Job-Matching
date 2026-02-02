import time
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
)

# =========================
# CONFIG
# =========================
QUERY = "data coop"
LOCATION = "Canada"
MAX_PAGES = 10
OUTPUT_FILE = "indeed_data_coop_canada.csv"
BASE_URL = "https://ca.indeed.com/jobs"

# =========================
# SET UP DRIVER
# =========================
def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--start-maximized")
    return webdriver.Chrome(options=chrome_options)

# =========================
# SCRAPER
# =========================
def scrape_indeed_coop():
    driver = create_driver()
    wait = WebDriverWait(driver, 15)

    results = []
    seen_jobs = set()  # deduplicate overlapping pages

    try:
        for page in range(MAX_PAGES):
            start = page * 10
            print(f"[INFO] Fetching page {page + 1}")

            driver.get(
                f"{BASE_URL}?q={QUERY.replace(' ', '+')}&l={LOCATION}&start={start}"
            )

            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.job_seen_beacon")
                    )
                )
            except TimeoutException:
                print("[INFO] No more pages")
                break

            job_cards = driver.find_elements(By.CSS_SELECTOR, "div.job_seen_beacon")
            print(f"[INFO] Found {len(job_cards)} job cards")

            if not job_cards:
                break

            for card in job_cards:
                try:
                    # ---- TITLE ----
                    title = card.find_element(
                        By.CSS_SELECTOR, "h2.jobTitle span"
                    ).text.strip()

                    # ---- COMPANY ----
                    try:
                        company = card.find_element(
                            By.CSS_SELECTOR, "span[data-testid='company-name']"
                        ).text.strip()
                    except NoSuchElementException:
                        company = "Not specified"

                    # ---- LOCATION ----
                    try:
                        location = card.find_element(
                            By.CSS_SELECTOR, "div[data-testid='text-location']"
                        ).text.strip()
                    except NoSuchElementException:
                        location = "Not specified"

                    # ---- JOB LINK (NEW) ----
                    job_link = card.find_element(
                        By.CSS_SELECTOR, "a"
                    ).get_attribute("href")

                    job_key = f"{title}|{company}|{location}"
                    if job_key in seen_jobs:
                        continue
                    seen_jobs.add(job_key)

                    # ---- OPEN JOB DETAIL PAGE ----
                    driver.execute_script("window.open(arguments[0]);", job_link)
                    driver.switch_to.window(driver.window_handles[-1])

                    # ---- JOB DESCRIPTION ----
                    try:
                        desc_elem = wait.until(
                            EC.presence_of_element_located(
                                (By.ID, "jobDescriptionText")
                            )
                        )
                        job_description = desc_elem.text.strip()
                    except TimeoutException:
                        job_description = "Not specified"

                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

                    results.append(
                        {
                            "job_title": title,
                            "company": company,
                            "location": location,
                            "job_link": job_link,              # ✅ added
                            "job_description": job_description,
                        }
                    )

                except StaleElementReferenceException:
                    print("[WARN] Stale element, skipping job")
                except Exception as e:
                    print(f"[WARN] Skipping job due to error: {e}")

            time.sleep(2)

    finally:
        driver.quit()

    return results

# =========================
# SAVE TO CSV
# =========================
def save_to_csv(jobs):
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "job_title",
                "company",
                "location",
                "job_link",          # ✅ added
                "job_description",
            ],
        )
        writer.writeheader()
        writer.writerows(jobs)

    print(f"[INFO] Saved {len(jobs)} jobs to {OUTPUT_FILE}")

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    jobs = scrape_indeed_coop()
    save_to_csv(jobs)

