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

    # Number of Images - Using slider instead of spinbox
    ttk.Label(main_frame, text="Images per Term:").grid(row=2, column=0, sticky='w', pady=5)
    num_images_var = tk.IntVar(value=num_images)
    num_images_slider = ttk.Scale(main_frame, from_=1, to=80, orient='horizontal',
                                 variable=num_images_var, length=200)
    num_images_slider.grid(row=2, column=1, sticky='ew', pady=5)
    # Add a label to show current value
    num_images_label = ttk.Label(main_frame, text=f"{num_images_var.get()}")
    num_images_label.grid(row=2, column=2, sticky='w', pady=5)
    # Update label when slider moves
    def update_num_images_label(*args):
        num_images_label.config(text=f"{num_images_var.get()}")
    num_images_var.trace_add('write', update_num_images_label)

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
                                     'vi-VN', 'cs-CZ', 'da-DK', 'fi-Fi', 'uk-UA', 'el-GR',
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