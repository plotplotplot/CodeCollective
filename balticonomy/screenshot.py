from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

options = Options()
options.add_argument("--headless")
options.add_argument("--window-size=800,800")

driver = webdriver.Remote(
    command_executor='http://localhost:4444/wd/hub',
    options=options
)

driver.get("https://standwithcrypto.org")
time.sleep(2)  # allow time to fully load the site
driver.save_screenshot("./screenshots/standwithcrypto.png")
driver.quit()
