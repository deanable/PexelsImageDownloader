import tkinter as tk
import winreg
from tkinter import filedialog
from tkinter import messagebox
import requests
import os
import threading
import io
from PIL import Image

# Function to download images
def download_images(api_key, search_terms, num_images, output_folder, status_label):
    headers = {"Authorization": api_key}
    if not api_key:
        status_label.config(text="Invalid API Key")
        return

    for term in search_terms:
        term = term.strip()
        if not term:
            continue

        term_folder = os.path.join(output_folder, term)
        os.makedirs(term_folder, exist_ok=True)
        status_label.config(text=f"Created folder for '{term}'")

        url = "https://api.pexels.com/v1/search"
        params = {"query": term, "per_page": 80}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        if not data["photos"]:
            status_label.config(text=f"No results for '{term}'")
            continue

        images_downloaded = 0
        for photo in data["photos"]:
            img_id = photo["id"]
            img_url = photo["src"]["original"]

            img_ext = os.path.splitext(img_url)[1]
            filename = os.path.join(term_folder, f"{img_id}{img_ext}")

            if os.path.exists(filename):
                continue

            try:
                img_response = requests.get(img_url, stream=True)
                img_response.raise_for_status()

                with open(filename, "wb") as f:
                    for chunk in img_response.iter_content(1024):
                        f.write(chunk)

                images_downloaded += 1
                status_label.config(text=f"Downloaded image {img_id} for '{term}'")

            except requests.exceptions.RequestException as e:
                status_label.config(text=f"Error downloading image {img_id}: {e}")

        if images_downloaded == 0:
            status_label.config(text=f"No images downloaded for '{term}'")

    status_label.config(text="Download complete.")

def create_gui():
    # Load saved values from the registry
    try:
        with winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER) as registry_key:
            with winreg.OpenKey(registry_key, r"Software\PexelsImageDownloader", 0, winreg.KEY_READ) as key:
                api_key = winreg.QueryValueEx(key, "api_key")[0]
                search_terms = winreg.QueryValueEx(key, "search_terms")[0]
                num_images = winreg.QueryValueEx(key, "num_images")[0]
                output_folder = winreg.QueryValueEx(key, "output_folder")[0]
    except Exception:
        api_key = ""
        search_terms = ""
        num_images = 100
        output_folder = ""

    root = tk.Tk()
    root.title("Pexels Image Downloader")

    tk.Label(root, text="Pexels API Key:").grid(row=0, column=0)
    api_key_entry = tk.Entry(root, show="*")
    api_key_entry.grid(row=0, column=1)
    api_key_entry.insert(0, api_key)

    tk.Label(root, text="Search Terms (comma-separated):").grid(row=1, column=0)
    search_entry = tk.Entry(root)
    search_entry.grid(row=1, column=1)
    search_entry.insert(0, search_terms)

    tk.Label(root, text="Images per Term:").grid(row=2, column=0)
    num_images_slider = tk.Scale(root, from_=100, to=1000, orient="horizontal")
    num_images_slider.grid(row=2, column=1)
    num_images_slider.set(num_images)

    tk.Label(root, text="Output Folder:").grid(row=3, column=0)
    folder_entry = tk.Entry(root)
    folder_entry.grid(row=3, column=1)
    folder_entry.insert(0, output_folder)
    folder_button = tk.Button(root, text="Browse", command=lambda: browse_folder(folder_entry))
    folder_button.grid(row=3, column=2)

    status_label = tk.Label(root, text="Ready")
    status_label.grid(row=4, column=0, columnspan=3)

    download_button = tk.Button(root, text="Download", command=lambda: start_download(api_key_entry, search_entry.get(), num_images_slider.get(), folder_entry.get(), status_label, download_button))
    download_button.grid(row=5, column=0, columnspan=3)

    root.mainloop()

def start_download(api_key_entry, search_input, num_images, output_folder, status_label, download_button):
    api_key = api_key_entry.get()
    if not api_key:
        status_label.config(text="Invalid API Key")
        return

    if not all([api_key, search_input, output_folder]):
        messagebox.showerror("Error", "API Key, Search Terms, and Output Folder cannot be empty.")
        return

    search_terms = [term.strip() for term in search_input.split(",")]

    download_button.config(state=tk.DISABLED)

    threading.Thread(
        target=download_images,
        args=(api_key, search_terms, num_images, output_folder, status_label),
        daemon=True
    ).start()

    # Save values to the registry
    save_to_registry(api_key, search_input, num_images, output_folder)

def browse_folder(entry):
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        entry.delete(0, tk.END)
        entry.insert(0, folder_selected)

# Function to save values to the registry
def save_to_registry(api_key, search_terms, num_images, output_folder):
    try:
        with winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER) as registry_key:
            with winreg.CreateKey(registry_key, r"Software\PexelsImageDownloader") as key:
                winreg.SetValueEx(key, "api_key", 0, winreg.REG_SZ, api_key)
                winreg.SetValueEx(key, "search_terms", 0, winreg.REG_SZ, search_terms)
                winreg.SetValueEx(key, "num_images", 0, winreg.REG_DWORD, num_images)
                winreg.SetValueEx(key, "output_folder", 0, winreg.REG_SZ, output_folder)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save values to the registry: {e}")

# Function to load values from the registry
def load_from_registry():
    try:
        with winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER) as registry_key:
            with winreg.OpenKey(registry_key, r"Software\PexelsImageDownloader", 0, winreg.KEY_READ) as key:
                api_key = winreg.QueryValueEx(key, "api_key")[0]
                search_terms = winreg.QueryValueEx(key, "search_terms")[0]
                num_images = winreg.QueryValueEx(key, "num_images")[0]
                output_folder = winreg.QueryValueEx(key, "output_folder")[0]
        return api_key, search_terms, num_images, output_folder
    except Exception:
        return "", "", 100, ""

if __name__ == "__main__":
    create_gui()
