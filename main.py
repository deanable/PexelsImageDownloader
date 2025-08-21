import tkinter as tk
import winreg
from tkinter import filedialog, ttk
from tkinter import messagebox
import requests
import os
import threading
import time
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pexels_downloader.log'),
        logging.StreamHandler()
    ]
)

@dataclass
class DownloadStats:
    total_searches: int = 0
    successful_downloads: int = 0
    failed_downloads: int = 0
    skipped_files: int = 0
    api_calls: int = 0
    start_time: Optional[datetime] = None

class RateLimiter:
    def __init__(self, calls_per_minute: int = 50):
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call_time = 0

    def wait_if_needed(self):
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time

        if time_since_last_call < self.min_interval:
            wait_time = self.min_interval - time_since_last_call
            logging.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)

        self.last_call_time = time.time()

class PexelsAPI:
    BASE_URL = "https://api.pexels.com/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"Authorization": api_key}
        self.rate_limiter = RateLimiter()
        self.session = self._create_session()
        self.stats = DownloadStats()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def search_photos(self, query: str, per_page: int = 80,
                     orientation: Optional[str] = None,
                     size: Optional[str] = None,
                     color: Optional[str] = None,
                     locale: Optional[str] = None) -> Optional[Dict]:

        self.rate_limiter.wait_if_needed()
        self.stats.api_calls += 1

        params = {
            "query": query,
            "per_page": min(per_page, 80)
        }

        # Add optional parameters
        if orientation and orientation in ['landscape', 'portrait', 'square']:
            params['orientation'] = orientation
        if size and size in ['large', 'medium', 'small']:
            params['size'] = size
        if color:
            params['color'] = color
        if locale:
            params['locale'] = locale

        try:
            logging.info(f"Searching for '{query}' with params: {params}")
            response = self.session.get(
                f"{self.BASE_URL}/search",
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()

            # Check rate limit headers
            remaining = response.headers.get('X-Ratelimit-Remaining')
            if remaining and int(remaining) < 10:
                logging.warning(f"API rate limit remaining: {remaining}")

            return response.json()

        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise ValueError("Invalid API key")
            elif response.status_code == 429:
                raise Exception("Rate limit exceeded. Please wait before making more requests.")
            else:
                raise Exception(f"API error: {e}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {e}")

def download_images(api_key, search_terms, num_images, output_folder,
                   status_label, progress_bar, orientation=None,
                   size=None, color=None, locale=None):
    """Enhanced image download function with comprehensive error handling and rate limiting"""

    if not api_key:
        status_label.config(text="Invalid API Key")
        return

    if not search_terms or not output_folder:
        messagebox.showerror("Error", "Search terms and output folder are required.")
        return

    # Initialize API client
    try:
        api = PexelsAPI(api_key)
        api.stats.start_time = datetime.now()
    except Exception as e:
        status_label.config(text=f"Failed to initialize API: {e}")
        return

    # Create output folder if it doesn't exist
    try:
        os.makedirs(output_folder, exist_ok=True)
    except Exception as e:
        status_label.config(text=f"Failed to create output folder: {e}")
        return

    status_label.config(text="Starting download process...")
    progress_bar['value'] = 0

    total_operations = len(search_terms)
    completed_operations = 0

    for term in search_terms:
        term = term.strip()
        if not term:
            continue

        term_folder = os.path.join(output_folder, term.replace('/', '_').replace('\\', '_'))
        try:
            os.makedirs(term_folder, exist_ok=True)
        except Exception as e:
            logging.error(f"Failed to create folder for '{term}': {e}")
            continue

        status_label.config(text=f"Processing '{term}'...")
        api.stats.total_searches += 1

        try:
            # Search for photos
            data = api.search_photos(
                query=term,
                per_page=min(num_images, 80),
                orientation=orientation,
                size=size,
                color=color,
                locale=locale
            )

            if not data or not data.get("photos"):
                logging.warning(f"No results found for '{term}'")
                status_label.config(text=f"No results for '{term}'")
                completed_operations += 1
                progress_bar['value'] = (completed_operations / total_operations) * 100
                continue

            photos = data["photos"]
            logging.info(f"Found {len(photos)} photos for '{term}'")

            images_downloaded = 0
            images_skipped = 0
            images_failed = 0

            for i, photo in enumerate(photos):
                if images_downloaded >= num_images:
                    break

                img_id = photo["id"]
                img_url = photo["src"]["original"]

                # Generate filename
                img_ext = os.path.splitext(img_url)[1] or '.jpg'
                filename = os.path.join(term_folder, f"{img_id}{img_ext}")

                # Skip if file already exists
                if os.path.exists(filename):
                    images_skipped += 1
                    api.stats.skipped_files += 1
                    continue

                # Download image with retry logic
                if download_single_image(img_url, filename, api.session):
                    images_downloaded += 1
                    api.stats.successful_downloads += 1
                    status_label.config(text=f"Downloaded {images_downloaded} images for '{term}'")
                else:
                    images_failed += 1
                    api.stats.failed_downloads += 1

                # Update progress within term
                term_progress = ((i + 1) / len(photos)) * 100
                status_label.config(text=f"Processing '{term}': {term_progress:.1f}%")

            completed_operations += 1
            progress_bar['value'] = (completed_operations / total_operations) * 100

            # Log results for this term
            logging.info(f"Completed '{term}': {images_downloaded} downloaded, "
                        f"{images_skipped} skipped, {images_failed} failed")

        except ValueError as e:
            status_label.config(text=f"Authentication error: {e}")
            logging.error(f"Authentication error for '{term}': {e}")
            break
        except Exception as e:
            status_label.config(text=f"Error processing '{term}': {e}")
            logging.error(f"Error processing '{term}': {e}")
            completed_operations += 1
            progress_bar['value'] = (completed_operations / total_operations) * 100

    # Final statistics
    end_time = datetime.now()
    duration = end_time - api.stats.start_time if api.stats.start_time else None

    stats_message = (f"Download complete!\n"
                    f"Searches: {api.stats.total_searches}\n"
                    f"Downloaded: {api.stats.successful_downloads}\n"
                    f"Skipped: {api.stats.skipped_files}\n"
                    f"Failed: {api.stats.failed_downloads}\n"
                    f"API calls: {api.stats.api_calls}")

    if duration:
        stats_message += f"\nDuration: {duration.total_seconds():.1f}s"

    status_label.config(text="Download complete!")
    messagebox.showinfo("Download Complete", stats_message)
    logging.info(stats_message)

def download_single_image(url: str, filename: str, session: requests.Session,
                         max_retries: int = 3) -> bool:
    """Download a single image with retry logic"""

    for attempt in range(max_retries):
        try:
            response = session.get(url, stream=True, timeout=30)
            response.raise_for_status()

            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logging.debug(f"Successfully downloaded {filename}")
            return True

        except Exception as e:
            logging.warning(f"Attempt {attempt + 1} failed for {filename}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logging.error(f"Failed to download {filename} after {max_retries} attempts")
                return False

def create_gui():
    """Create enhanced GUI with additional search parameters and better UX"""

    # Load saved values from the registry
    try:
        with winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER) as registry_key:
            with winreg.OpenKey(registry_key, r"Software\PexelsImageDownloader", 0, winreg.KEY_READ) as key:
                api_key = winreg.QueryValueEx(key, "api_key")[0]
                search_terms = winreg.QueryValueEx(key, "search_terms")[0]
                num_images = winreg.QueryValueEx(key, "num_images")[0]
                output_folder = winreg.QueryValueEx(key, "output_folder")[0]
                orientation = winreg.QueryValueEx(key, "orientation")[0]
                size = winreg.QueryValueEx(key, "size")[0]
                color = winreg.QueryValueEx(key, "color")[0]
                locale = winreg.QueryValueEx(key, "locale")[0]
    except Exception:
        api_key = ""
        search_terms = ""
        num_images = 50  # Reduced default to be more reasonable
        output_folder = ""
        orientation = ""
        size = ""
        color = ""
        locale = ""

    root = tk.Tk()
    root.title("Enhanced Pexels Image Downloader")
    root.geometry("600x500")
    root.resizable(True, True)

    # Create notebook for tabs
    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True, padx=10, pady=10)

    # Main tab
    main_frame = ttk.Frame(notebook)
    notebook.add(main_frame, text='Download')

    # Settings tab
    settings_frame = ttk.Frame(notebook)
    notebook.add(settings_frame, text='Advanced Settings')

    # API Key
    ttk.Label(main_frame, text="Pexels API Key:").grid(row=0, column=0, sticky='w', pady=5)
    api_key_entry = ttk.Entry(main_frame, show="*", width=50)
    api_key_entry.grid(row=0, column=1, columnspan=2, sticky='ew', pady=5)
    api_key_entry.insert(0, api_key)

    # Search Terms
    ttk.Label(main_frame, text="Search Terms (comma-separated):").grid(row=1, column=0, sticky='w', pady=5)
    search_entry = ttk.Entry(main_frame, width=50)
    search_entry.grid(row=1, column=1, columnspan=2, sticky='ew', pady=5)
    search_entry.insert(0, search_terms)

    # Number of Images
    ttk.Label(main_frame, text="Images per Term:").grid(row=2, column=0, sticky='w', pady=5)
    num_images_var = tk.IntVar(value=num_images)
    num_images_spinbox = ttk.Spinbox(main_frame, from_=1, to=80, textvariable=num_images_var, width=10)
    num_images_spinbox.grid(row=2, column=1, sticky='w', pady=5)

    # Output Folder
    ttk.Label(main_frame, text="Output Folder:").grid(row=3, column=0, sticky='w', pady=5)
    folder_entry = ttk.Entry(main_frame, width=40)
    folder_entry.grid(row=3, column=1, sticky='ew', pady=5)
    folder_entry.insert(0, output_folder)
    folder_button = ttk.Button(main_frame, text="Browse",
                              command=lambda: browse_folder(folder_entry))
    folder_button.grid(row=3, column=2, sticky='w', pady=5)

    # Progress bar
    progress_bar = ttk.Progressbar(main_frame, orient='horizontal', mode='determinate')
    progress_bar.grid(row=4, column=0, columnspan=3, sticky='ew', pady=10)

    # Status label
    status_label = ttk.Label(main_frame, text="Ready", relief='sunken', anchor='w')
    status_label.grid(row=5, column=0, columnspan=3, sticky='ew', pady=5)

    # Advanced Settings tab
    ttk.Label(settings_frame, text="Orientation:").grid(row=0, column=0, sticky='w', pady=5)
    orientation_var = tk.StringVar(value=orientation)
    orientation_combo = ttk.Combobox(settings_frame, textvariable=orientation_var,
                                   values=['', 'landscape', 'portrait', 'square'], width=20)
    orientation_combo.grid(row=0, column=1, sticky='w', pady=5)

    ttk.Label(settings_frame, text="Size:").grid(row=1, column=0, sticky='w', pady=5)
    size_var = tk.StringVar(value=size)
    size_combo = ttk.Combobox(settings_frame, textvariable=size_var,
                             values=['', 'large', 'medium', 'small'], width=20)
    size_combo.grid(row=1, column=1, sticky='w', pady=5)

    ttk.Label(settings_frame, text="Color:").grid(row=2, column=0, sticky='w', pady=5)
    color_var = tk.StringVar(value=color)
    color_combo = ttk.Combobox(settings_frame, textvariable=color_var,
                              values=['', 'red', 'orange', 'yellow', 'green', 'turquoise',
                                    'blue', 'violet', 'pink', 'brown', 'black', 'gray', 'white'], width=20)
    color_combo.grid(row=2, column=1, sticky='w', pady=5)

    ttk.Label(settings_frame, text="Locale:").grid(row=3, column=0, sticky='w', pady=5)
    locale_var = tk.StringVar(value=locale)
    locale_combo = ttk.Combobox(settings_frame, textvariable=locale_var,
                               values=['', 'en-US', 'pt-BR', 'es-ES', 'ca-ES', 'de-DE',
                                     'it-IT', 'fr-FR', 'sv-SE', 'id-ID', 'pl-PL', 'ja-JP',
                                     'zh-TW', 'zh-CN', 'ko-KR', 'th-TH', 'nl-NL', 'hu-HU',
                                     'vi-VN', 'cs-CZ', 'da-DK', 'fi-FI', 'uk-UA', 'el-GR',
                                     'ro-RO', 'nb-NO', 'sk-SK', 'tr-TR', 'ru-RU'], width=20)
    locale_combo.grid(row=3, column=1, sticky='w', pady=5)

    # Buttons frame
    button_frame = ttk.Frame(main_frame)
    button_frame.grid(row=6, column=0, columnspan=3, pady=10)

    download_button = ttk.Button(button_frame, text="Start Download",
                                command=lambda: start_download(
                                    api_key_entry, search_entry.get(), num_images_var.get(),
                                    folder_entry.get(), status_label, progress_bar, download_button,
                                    orientation_var.get(), size_var.get(), color_var.get(), locale_var.get()
                                ))
    download_button.pack(side='left', padx=5)

    # Add tooltips and help
    help_button = ttk.Button(button_frame, text="Help",
                           command=lambda: show_help())
    help_button.pack(side='left', padx=5)

    # Configure grid weights
    main_frame.columnconfigure(1, weight=1)
    settings_frame.columnconfigure(1, weight=1)

    root.mainloop()

def start_download(api_key_entry, search_input, num_images, output_folder,
                  status_label, progress_bar, download_button, orientation="",
                  size="", color="", locale=""):
    """Enhanced download starter with comprehensive parameter support"""

    api_key = api_key_entry.get()
    if not api_key:
        messagebox.showerror("Error", "API Key is required.")
        return

    if not search_input or not output_folder:
        messagebox.showerror("Error", "Search terms and output folder are required.")
        return

    if not os.path.exists(output_folder):
        try:
            os.makedirs(output_folder, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create output folder: {e}")
            return

    search_terms = [term.strip() for term in search_input.split(",") if term.strip()]

    if not search_terms:
        messagebox.showerror("Error", "Please enter at least one valid search term.")
        return

    # Disable button and show progress
    download_button.config(state=tk.DISABLED, text="Downloading...")
    progress_bar['value'] = 0
    status_label.config(text="Initializing download...")

    # Start download in separate thread
    def download_thread():
        try:
            download_images(
                api_key, search_terms, num_images, output_folder,
                status_label, progress_bar, orientation, size, color, locale
            )
        finally:
            download_button.config(state=tk.NORMAL, text="Start Download")
            progress_bar['value'] = 100

    threading.Thread(target=download_thread, daemon=True).start()

    # Save values to registry
    save_to_registry(api_key, search_input, num_images, output_folder,
                    orientation, size, color, locale)

def browse_folder(entry):
    """Browse for output folder"""
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        entry.delete(0, tk.END)
        entry.insert(0, folder_selected)

def show_help():
    """Show help information"""
    help_text = """Pexels Image Downloader Help:

1. API Key: Get your free API key from https://www.pexels.com/api/
2. Search Terms: Enter terms separated by commas (e.g., "nature, ocean, mountains")
3. Images per Term: Maximum 80 images per search term
4. Output Folder: Choose where to save downloaded images

Advanced Settings:
- Orientation: landscape, portrait, or square
- Size: large (24MP), medium (12MP), or small (4MP)
- Color: Filter by dominant color
- Locale: Search in specific language

Rate Limits:
- 200 requests per hour
- 20,000 requests per month
- Images are cached to avoid re-downloads

For more information, visit: https://www.pexels.com/api/documentation/"""

    messagebox.showinfo("Help", help_text)

def save_to_registry(api_key, search_terms, num_images, output_folder,
                    orientation="", size="", color="", locale=""):
    """Save all settings to Windows registry"""
    try:
        with winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER) as registry_key:
            with winreg.CreateKey(registry_key, r"Software\PexelsImageDownloader") as key:
                winreg.SetValueEx(key, "api_key", 0, winreg.REG_SZ, api_key)
                winreg.SetValueEx(key, "search_terms", 0, winreg.REG_SZ, search_terms)
                winreg.SetValueEx(key, "num_images", 0, winreg.REG_DWORD, num_images)
                winreg.SetValueEx(key, "output_folder", 0, winreg.REG_SZ, output_folder)
                winreg.SetValueEx(key, "orientation", 0, winreg.REG_SZ, orientation)
                winreg.SetValueEx(key, "size", 0, winreg.REG_SZ, size)
                winreg.SetValueEx(key, "color", 0, winreg.REG_SZ, color)
                winreg.SetValueEx(key, "locale", 0, winreg.REG_SZ, locale)
        logging.info("Settings saved to registry")
    except Exception as e:
        logging.error(f"Failed to save settings to registry: {e}")
        messagebox.showwarning("Warning", f"Failed to save settings: {e}")

if __name__ == "__main__":
    create_gui()
