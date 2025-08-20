import PySimpleGUI as sg
import requests
import os
import threading
import io
from PIL import Image

# Function to download images
def download_images(api_key, search_terms, num_images, output_folder, window):
    headers = {"Authorization": api_key}
    for term in search_terms:
        term = term.strip()
        if not term:
            continue

        term_folder = os.path.join(output_folder, term)
        os.makedirs(term_folder, exist_ok=True)
        window["-STATUS-"].update(f"Created folder for '{term}'")

        url = "https://api.pexels.com/v1/search"
        params = {"query": term, "per_page": 80}  # Max per_page is 80
        images_downloaded = 0

        while images_downloaded < num_images:
            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                if not data["photos"]:
                    window["-STATUS-"].update(f"No results for '{term}'.")
                    break

                for photo in data["photos"]:
                    if images_downloaded >= num_images:
                        break

                    img_id = photo["id"]
                    img_url = photo["src"]["original"]
                    img_ext = os.path.splitext(img_url)[1]
                    filename = os.path.join(term_folder, f"{img_id}{img_ext}")

                    if os.path.exists(filename):
                        continue

                    try:
                        img_response = requests.get(img_url, stream=True)
                        img_response.raise_for_status()

                        # Check if the content is a valid image
                        image_data = img_response.content
                        try:
                            Image.open(io.BytesIO(image_data)).verify()
                        except Exception:
                            window["-STATUS-"].update(f"Skipping invalid image for '{term}'")
                            continue

                        with open(filename, "wb") as f:
                            f.write(image_data)

                        images_downloaded += 1
                        progress = f"Downloading {images_downloaded}/{num_images} for '{term}'"
                        window["-STATUS-"].update(progress)

                    except requests.exceptions.RequestException as e:
                        window["-STATUS-"].update(f"Error downloading image {img_id}: {e}")

                if "next_page" in data and data["next_page"]:
                    url = data["next_page"]
                else:
                    break # No more pages

            except requests.exceptions.RequestException as e:
                window["-STATUS-"].update(f"API Error for '{term}': {e}")
                break
            except Exception as e:
                window["-STATUS-"].update(f"An error occurred: {e}")
                break

    window["-DOWNLOAD-"].update(disabled=False)
    window["-STATUS-"].update("Download complete.")

# GUI Layout
layout = [
    [sg.Text("Pexels API Key:"), sg.Input(key="-API_KEY-", password_char="*")],
    [sg.Text("Search Terms (comma-separated):"), sg.Input(key="-SEARCH-")],
    [sg.Text("Images per Term:"), sg.Slider(range=(100, 1000), default_value=100, resolution=100, orientation="h", key="-NUM_IMAGES-")],
    [sg.Text("Output Folder:"), sg.Input(key="-FOLDER-", readonly=True), sg.FolderBrowse()],
    [sg.Button("Download", key="-DOWNLOAD-")],
    [sg.StatusBar("Ready", key="-STATUS-", size=(60, 1))]
]

window = sg.Window("Pexels Image Downloader", layout)

# Event Loop
while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED:
        break
    if event == "-DOWNLOAD-":
        api_key = values["-API_KEY-"]
        search_input = values["-SEARCH-"]
        num_images = int(values["-NUM_IMAGES-"])
        output_folder = values["-FOLDER-"]

        # Input Validation
        if not all([api_key, search_input, output_folder]):
            sg.popup_error("API Key, Search Terms, and Output Folder cannot be empty.")
            continue

        search_terms = [term.strip() for term in search_input.split(",")]

        window["-DOWNLOAD-"].update(disabled=True)

        # Run download in a separate thread to keep the GUI responsive
        threading.Thread(
            target=download_images,
            args=(api_key, search_terms, num_images, output_folder, window),
            daemon=True
        ).start()

window.close()
