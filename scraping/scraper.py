"""CACTI graph scraper using Selenium.

Security and reliability improvements:
- Configurable headless mode via settings
- Request timeouts with retry
- Integration with centralized logging
"""

from graph_storage import save_graph_info, save_error
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re

from progress_tracker import progress
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
import traceback
import time
from datetime import datetime
import logging

# Import configuration
try:
    from config import settings
except ImportError:
    class _FallbackSettings:
        SELENIUM_HEADLESS = False
        SELENIUM_WAIT_TIMEOUT = 15
        SELENIUM_PAGE_LOAD_TIMEOUT = 30
        REQUEST_TIMEOUT = 30
        RETRY_MAX_ATTEMPTS = 3
    settings = _FallbackSettings()

logger = logging.getLogger(__name__)


def get_chrome_options() -> Options:
    """Get Chrome options with configurable headless mode."""
    chrome_options = Options()
    chrome_options.add_argument("--disable-features=PasswordCheck,AutofillKeyedPasswords,AutofillServerCommunication")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--incognito")
    
    # Headless mode from config
    if getattr(settings, 'SELENIUM_HEADLESS', False):
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        logger.info("Running Chrome in headless mode")
    else:
        chrome_options.add_argument("--start-maximized")
    
    return chrome_options


def get_requests_session() -> requests.Session:
    """Create a requests session with retry and timeout configuration."""
    session = requests.Session()
    
    # Configure retry strategy with exponential backoff
    retry_strategy = Retry(
        total=getattr(settings, 'RETRY_MAX_ATTEMPTS', 3),
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def sanitize_filename(title: str) -> str:
    """Sanitize filename by replacing invalid characters."""
    sanitized_title = re.sub(r'[\/:*?"<>|]', '_', title)
    max_length = 255
    return sanitized_title[:max_length]


def save_graph_image(graph_url: str, title: str, driver, custom_folder: str | None = None) -> str | None:
    """Download graph image with timeout and retry."""
    try:
        filename = f"{sanitize_filename(title)}.png"
        
        if custom_folder:
            local_path = os.path.join(custom_folder, filename)
        else:
            local_path = os.path.join("downloaded_graphs", filename)
        
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        # Use configured session with retry
        session = get_requests_session()
        
        # Transfer cookies from Selenium
        for cookie in driver.get_cookies():
            session.cookies.set(cookie['name'], cookie['value'])

        logger.info(f"Downloading image from {graph_url}...")
        
        # Use configured timeout
        timeout = getattr(settings, 'REQUEST_TIMEOUT', 30)
        response = session.get(graph_url, timeout=timeout)

        if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
            with open(local_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"Gambar berhasil disimpan ke {local_path}")
            return local_path
        else:
            logger.info(f"[ERROR] Gagal mengunduh gambar. Status Code: {response.status_code}, Content-Type: {response.headers.get('Content-Type')}")
            return None

    except Exception as e:
        logger.info(f"[ERROR] Gagal mendownload gambar: {str(e)}")
        return None

def extract_short_title(full_title: str) -> str:
    """
    Extract a meaningful short title from CACTI graph full title.
    
    Examples:
        Input:  "Zooming Graph 'bndg.ro.corp2 - Bundle-Ether4.1562 - isp-cust-pre 35230536 - fsr-bsibatununggallx - 10'"
        Output: "fsr-bsibatununggallx"
        
        Input:  "Zooming Graph 'router - isp-cust 12345 - customer-name'"
        Output: "customer-name"
    """
    try:
        # Remove 'Zooming Graph' prefix and quotes
        cleaned = full_title.replace("Zooming Graph", "").strip()
        cleaned = cleaned.strip("'\"")
        
        # Split by ' - ' separator
        parts = [p.strip() for p in cleaned.split(' - ') if p.strip()]
        
        if not parts:
            return full_title
        
        # Strategy 1: Look for customer identifier patterns (fsr-*, cust-*, etc.)
        # These are typically the most meaningful identifiers
        customer_patterns = [
            r'\bfsr-[\w]+',      # fsr-bsibatununggallx
            r'\bcust-[\w]+',     # cust-something
            r'\bcustomer-[\w]+', # customer-name
            r'\bisp-cust\s+\d+', # isp-cust 35230536
        ]
        
        for pattern in customer_patterns:
            for part in reversed(parts):  # Search from end
                match = re.search(pattern, part, re.IGNORECASE)
                if match:
                    # For patterns like "isp-cust-pre 35230536 - fsr-xyz", prefer fsr-xyz
                    if pattern.startswith(r'\bfsr') or pattern.startswith(r'\bcust'):
                        return match.group(0)
        
        # Strategy 2: If last part is just a number, use second-to-last
        # Example: "fsr-bsibatununggallx - 10" -> "fsr-bsibatununggallx"
        last_part = parts[-1]
        if re.match(r'^\d+$', last_part) and len(parts) >= 2:
            # Return second-to-last, but extract identifier if it contains more
            second_last = parts[-2]
            # If second-to-last contains space-separated items, get the last meaningful one
            second_parts = second_last.split()
            if second_parts:
                # Prefer alphanumeric identifiers over pure numbers
                for sp in reversed(second_parts):
                    if re.match(r'^[\w-]+$', sp) and not re.match(r'^\d+$', sp):
                        return sp
                return second_parts[-1]
            return second_last
        
        # Strategy 3: Return last part (original behavior)
        short_title = last_part.replace("'", "").replace('"', '')
        return short_title
        
    except Exception as e:
        logger.warning(f"Failed to extract short title: {str(e)}")
        return full_title

def retry_on_stale_element(max_retries=3, delay=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except StaleElementReferenceException:
                    logger.warning(f"Stale element detected. Retrying {retries + 1}/{max_retries}...")
                    time.sleep(delay)
                    retries += 1
            raise Exception(f"[ERROR] Failed after {max_retries} retries due to stale element.")
        return wrapper
    return decorator

def check_and_click_zoom(driver, username):
    try:
        # 1. Cek apakah ada pesan "no data"
        no_data_markers = [
            "No data sources present",
            "Tidak ada data",
            "No matching records found"
        ]
        
        for marker in no_data_markers:
            if marker in driver.page_source:
                logger.warning(f"Data tidak tersedia untuk {username}")
                return False, f"Data tidak tersedia (Marker: {marker})"

        debug_dir = "Debug/debug_screenshots"
        os.makedirs(debug_dir, exist_ok=True)
        driver.save_screenshot(f"{debug_dir}/{username}_before_zoom_check.png")

        # 2. Multi-strategy untuk menemukan link Zoom
        zoom_selectors = [
            {"type": "xpath", "value": "//a[contains(@href,'graph.php?action=zoom')]"},
            {"type": "xpath", "value": "//a[img[contains(@src,'graph_image.php')]]"},
            {"type": "css", "value": "a.graph-zoom"},
            {"type": "xpath", "value": "//a[contains(@onclick,'graph_zoom')]"},
            {"type": "xpath", "value": "//a[contains(@class,'zoomLink')]"},
            {"type": "xpath", "value": "//a[contains(text(),'Zoom')]"},
            {"type": "xpath", "value": "//a[normalize-space(.)='Zoom']"},
            # Additional selector for img inside any a element
            {"type": "xpath", "value": "//a[.//img]"}
        ]

        for selector in zoom_selectors:
            try:
                if selector["type"] == "xpath":
                    zoom_link = WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located((By.XPATH, selector["value"]))
                    )
                else:
                    zoom_link = WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector["value"]))
                    )
                
                logger.info(f"[DEBUG] Link Zoom ditemukan dengan {selector['type']}: {selector['value']}")
                return True, zoom_link
            except Exception as e:
                logger.info(f"[DEBUG] Gagal menemukan Zoom link dengan selector {selector['value']}: {str(e)}")
                continue

        # 3. Fallback: Cek apakah ada grafik tanpa link zoom
        graph_images = driver.find_elements(By.XPATH, "//img[contains(@src,'graph_image.php')]")
        if graph_images:
            logger.warning(f"Grafik ditemukan tapi tanpa link Zoom untuk {username}")
            return False, "Grafik ada tetapi tidak ada link Zoom"
        
        return False, "Link Zoom tidak ditemukan dengan semua selector"

    except Exception as e:
        logger.error(f"Terjadi error dalam pencarian Zoom untuk {username}: {str(e)}")
        logger.error("Error detail:", exc_info=True)
        # Print full traceback untuk debugging lebih lanjut
        return False, f"Error dalam pencarian Zoom: {str(e)}"

@retry_on_stale_element(max_retries=3, delay=1)
def fill_filter_input(driver, username):
    filter_input = driver.find_element(By.NAME, 'filter')
    filter_input.clear()
    filter_input.send_keys(username)

# NOTE: Removed duplicate setup_logging() - use utils.logging_config.setup_logging instead

# Fungsi untuk mengotomatiskan login dan scraping untuk setiap username
def login_and_scrape(date1="2025-03-01 00:00", date2="2025-04-01 00:00", target_url="", userLogin=None, userPass=None, usernames=None, custom_folder=None):
    driver = None
    results = {
        "total_processed": 0,
        "success": 0,        # Integer, bukan list
        "failed": 0,         # Integer, bukan list
        "processed_usernames": [],
        "errors": []
    }


    progress.scraping['total'] = len(usernames)
    # Tentukan folder untuk menyimpan gambar lokal
    

    try:
        logger.info("Memulai WebDriver...")
        chrome_options = get_chrome_options()  # Use config-driven options
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        
        # Use configurable timeout
        wait_timeout = getattr(settings, 'SELENIUM_WAIT_TIMEOUT', 15)
        wait = WebDriverWait(driver, wait_timeout)

        logger.info(f"Membuka halaman login: {target_url}")
        driver.get(target_url)  # Gunakan URL dari parameter

        # # Telkom
        # print("[INFO] Mengisi username dan password...")
        # username_input = wait.until(EC.presence_of_element_located((By.NAME, 'login_username')))
        # password_input = driver.find_element(By.NAME, 'login_password')
        # login_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @value='Login']")))

        # username_input.send_keys({userLogin})
        # password_input.send_keys({userPass})
        # login_button.click()

        # FS
        logger.info("Mengisi username dan password...")
        username_input = wait.until(EC.presence_of_element_located((By.NAME, 'login_username')))
        password_input = driver.find_element(By.NAME, 'login_password')
        login_button = driver.find_element(By.CLASS_NAME, 'button--primary')

        username_input.send_keys(userLogin)
        password_input.send_keys(userPass)
        login_button.click()


        time.sleep(4)

        logger.info("Mengisi tanggal awal...")
        date1_input = wait.until(EC.presence_of_element_located((By.ID, "date1")))
        date1_input.clear()
        date1_input.send_keys(date1)  # Use the passed parameter

        logger.info("Mengisi tanggal akhir...")
        date2_input = driver.find_element(By.ID, "date2")
        date2_input.clear()
        date2_input.send_keys(date2)  # Use the passed parameter

        logger.info("Menekan tombol Refresh...")
        refresh_button = driver.find_element(By.NAME, "button_refresh_x")
        refresh_button.click()

        if custom_folder is None:
            now = datetime.now()
            timestamp_str = now.strftime("%Y-%m-%d_%H-%M-%S")
            base_folder = "downloaded_graphs"
            custom_folder = os.path.join(base_folder, f"scraping_{timestamp_str}")
        
        # Pastikan folder ada
        os.makedirs(custom_folder, exist_ok=True)
        logger.info(f"Gambar akan disimpan di: {custom_folder}")
        
        # Set folder global untuk digunakan di fungsi lain
        global current_scraping_folder
        current_scraping_folder = custom_folder

        # Proses otomatis untuk setiap username
        for i, username in enumerate(usernames, 1):
            results["total_processed"] += 1
            results["processed_usernames"].append(username)
            progress.scraping.update({
            'current': i,
            'total': len(usernames),
            'message': f'Memproses {username} ({i}/{len(usernames)})',
            'current_file': username,
            'status': 'running'
            })
            try:
                fill_filter_input(driver, username)

                logger.info("[DEBUG] Mencari tombol Go...")
                go_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@value='Go' and @title='Set/Refresh Filters']"))
                )
                if not go_button:
                    error_msg = f"Gagal Menemukan btton {username}"
                    logger.error(f"{error_msg}")
                    results["failed"] += 1
                    results["errors"].append({"username": username, "error": error_msg})
                logger.info("[DEBUG] Tombol Go ditemukan, mencoba klik...")
                # driver.save_screenshot(f"debug_{username}_before_go.png")
                go_button.click()
                logger.info("[DEBUG] Tombol Go diklik")
    
                # [Sebelum mencari link Zoom]
                logger.info(f"[DEBUG] Memeriksa ketersediaan data untuk {username}")

                # Gunakan fungsi deteksi zoom yang ditingkatkan
                zoom_found, zoom_result = check_and_click_zoom(driver, username)

                if not zoom_found:
                    error_msg = f"Gagal menemukan Zoom untuk {username}: {zoom_result}"
                    logger.error(f"{error_msg}")
                    
                    # IMPROVEMENT: Store diagnostics in per-run folder
                    # Use custom_folder if available, otherwise fallback to no_zoom_reports
                    if custom_folder:
                        no_zoom_dir = os.path.join(os.path.dirname(custom_folder), "diagnostics")
                    else:
                        no_zoom_dir = "no_zoom_reports"
                    os.makedirs(no_zoom_dir, exist_ok=True)  # exist_ok=True agar tidak error jika folder sudah ada
                    
                    # 2. Simpan screenshot ke folder baru
                    screenshot_path = os.path.join(no_zoom_dir, f"no_zoom_{username}.png")
                    driver.save_screenshot(screenshot_path)
                    
                    # (Opsional) Simpan HTML ke folder yang sama
                    # html_path = os.path.join(no_zoom_dir, f"no_zoom_{username}_page.html")
                    # with open(html_path, "w", encoding="utf-8") as f:
                    #     f.write(driver.page_source)
                    
                    # Simpan detail HTML untuk analisis
                    # with open(f"no_zoom_{username}_page.html", "w", encoding="utf-8") as f:
                    #     f.write(driver.page_source)
                    
                    save_error(f"NoZoom-{username}", driver.current_url, f"no_zoom_{username}.png", error_msg)
                    results["failed"] += 1
                    results["errors"].append({"username": username, "error": error_msg})
                    continue

                # Jika zoom ditemukan
                zoom_link = zoom_result
                logger.debug("Klik link Zoom...")
                try:
                    driver.execute_script("arguments[0].scrollIntoView({behavior:'smooth',block:'center'});", zoom_link)
                    time.sleep(1)  # Beri waktu untuk scroll
                    driver.execute_script("arguments[0].click();", zoom_link)
                except Exception as click_error:
                    error_msg = f"Invalid zoom {username}"
                    logger.error(f"{error_msg}")
                    logger.error(f"Gagal klik Zoom: {str(click_error)}")
                    results["failed"] += 1
                    results["errors"].append({"username": username, "error": error_msg})
                    continue

            except Exception as e:
                error_msg = f"Gagal Menemukan {username}"
                logger.error(f"{error_msg}")
                
                # Simpan error ke database
                short_title = f"Error-{username}"
                save_error(f"NoZoom-{username}", driver.current_url, f"no_zoom_{username}.png", error_msg)
                results["failed"] += 1
                results["errors"].append({"username": username, "error": error_msg})
                continue

            # Coba ambil gambar graph
            try:
                logger.info("Menunggu gambar Graph muncul setelah klik Zoom...")
                graph_img = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//img[contains(@src, 'graph_image.php')]"))
                )
                graph_src = graph_img.get_attribute("src")
                logger.info(f"Gambar Graph ditemukan: {graph_src}")

                # Lanjutkan dengan penyimpanan gambar dan data lainnya...
            except Exception as e:
                error_msg = f"Gagal Menemukan gambar {username}"
                logger.error(f"{error_msg}")
                logger.error(f"Gambar Graph tidak ditemukan untuk {username}. Error: {str(e)}")
                results["failed"] += 1
                results["errors"].append({"username": username, "error": error_msg})
                continue

            if not graph_src.startswith("http"):
                # Construct full URL from target_url parameter
                base_url = target_url.rstrip('/') if target_url else ""
                graph_src = base_url + "/" + graph_src.lstrip('/')

            logger.info("Mengambil judul grafik...")
            try:
                td_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//td[contains(., 'Zooming Graph')]"))
                )
                title_text = td_element.text.strip()
                
                # Use username as the filename since it's the reliable identifier
                # Example: fsr-bsimanyarlx, fsr-bsibatununggallx
                short_title = username
                
                logger.info(f"HASIL Username: {username}")
                logger.info(f"Judul pendek (filename): {short_title}")
                logger.info(f"Judul asli CACTI: {title_text}")
                logger.info(f"Gambar URL: {graph_src}")
                logger.debug(f"Folder tujuan: {custom_folder}")

                local_path = save_graph_image(graph_src, short_title, driver, custom_folder)

                if local_path:
                    save_graph_info(short_title, graph_src, local_path, "Sukses")
                    results["success"] += 1
                    logger.info(f"[SUCCESS] Processed {username} successfully - saved to {local_path}")
                else:
                    logger.error(f"[ERROR] Failed to save image for {username}")
                    results["failed"] += 1
                    results["errors"].append({"username": username, "error": "Failed to save image"})

            except Exception as e:
                error_msg = f"Gagal mengambil graph untuk {username}. Error: {str(e)}"
                logger.error(f"{error_msg}")
                results["failed"] += 1
                results["errors"].append({"username": username, "error": error_msg})
                continue                 


            # Klik Preview Mode (keluar dari blok try-except atas)
            try:
                logger.info("Klik link Preview Mode...")
                preview_link = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "Preview Mode"))
                )
                preview_link.click()

                logger.info("Menunggu halaman Preview Mode terbuka...")
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "filter"))
                )

                logger.info(f"Menekan tombol Go lagi untuk username: {username} di Preview Mode")
                go_button = driver.find_element(By.XPATH, "//input[@value='Go' and @title='Set/Refresh Filters']")
                go_button.click()

                time.sleep(2)

            except Exception as e:
                logger.error(f"Gagal klik Preview Mode untuk {username}. Lanjut username berikutnya...")
                continue


        # Summary report
        logger.info("\n===== SCRAPING SUMMARY =====")
        logger.info(f"Total usernames: {len(usernames)}")
        logger.info(f"Successful: {results['success']}")
        logger.info(f"Failed: {results['failed']}")
        logger.info(f"Missing: {len(usernames) - results['total_processed']}")

        progress.scraping['message'] = f'Selesai. Sukses: {results["success"]}, Gagal: {results["failed"]}'

        #     Calculate unprocessed usernames
        all_processed = set(results["processed_usernames"])
        all_usernames = set(usernames)
        unprocessed = all_usernames - all_processed

        # Ganti bagian ini di akhir fungsi login_and_scrape():
        with open("scraping_report.txt", "w") as report_file:
            report_file.write(f"SCRAPING REPORT\n")
            report_file.write(f"Date range: {date1} to {date2}\n")
            report_file.write(f"Total usernames: {len(usernames)}\n")
            report_file.write(f"Successful: {results['success']}\n")
            report_file.write(f"Failed: {results['failed']}\n\n")
            
            # Perbaikan: gunakan data yang benar
            processed_usernames = set(results["processed_usernames"])
            all_usernames = set(usernames)
            unprocessed = all_usernames - processed_usernames
            
            if unprocessed:
                report_file.write("UNPROCESSED USERNAMES:\n")
                for u in unprocessed:
                    report_file.write(f"{u}: Tidak diproses sama sekali (missed in loop)\n")
                report_file.write("\n")
            
            if results["errors"]:
                report_file.write("ERROR DETAILS:\n")
                for error in results["errors"]:
                    report_file.write(f"{error['username']}: {error['error']}\n")
                                                                                            
    
    except Exception as e:
        progress.scraping['message'] = f'Error saat memproses {username}: {str(e)}'
        traceback.print_exc()

    # Write report to file

    finally:
        if driver:
            logger.info("Menutup browser...")
            progress.scraping.update({
                'status': 'complete',
                'message': f'Scraping selesai! Sukses: {results["success"]}, Gagal: {results["failed"]}',
                'current_file': '',
                'current': len(usernames)
            })
            driver.quit()

if __name__ == '__main__':
    login_and_scrape()
