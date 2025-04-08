import os
import re
import requests
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter import messagebox
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Author: bigtajine
# Script Name: amazonImageDownloader.py
# Last Modified: 2025-04-08

# Country options for Amazon websites
COUNTRY_OPTIONS = {
    "Amazon.com": ("com", "en"),
    "Amazon.ca": ("ca", "en"),
    "Amazon.co.uk": ("co.uk", "en"),
    "Amazon.de": ("de", "de"),
    "Amazon.fr": ("fr", "fr"),
    "Amazon.it": ("it", "it"),
    "Amazon.es": ("es", "es"),
    "Amazon.com.mx": ("com.mx", "es"),
    "Amazon.in": ("in", "hi"),
    "Amazon.com.br": ("com.br", "pt"),
    "Amazon.au": ("au", "en"),
    "Amazon.nl": ("nl", "nl"),
    "Amazon.sg": ("sg", "en"),
    "Amazon.se": ("se", "sv"),
    "Amazon.pl": ("pl", "pl"),
    "Amazon.sa": ("sa", "ar"),
    "Amazon.ae": ("ae", "ar"),
    "Amazon.co.il": ("co.il", "he"),
    "Amazon.tr": ("tr", "tr")
}

def extract_image_urls(driver, asin, country):
    """Extract image URLs from an Amazon product page."""
    url = f'https://www.amazon.{country[0]}/dp/{asin}?th=1'
    driver.get(url)
    driver.implicitly_wait(10)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    scripts = soup.find_all('script')
    image_urls = []
    
    for script in scripts:
        if 'colorImages' in (script_content := script.string or ''):
            matches = re.findall(r'{"hiRes":(null|"https://m\.media-amazon\.com/images/I/[^\"]*"),"thumb":"https://m\.media-amazon\.com/images/I/[^\"]*","large":"(https://m\.media-amazon\.com/images/I/[^\"]*)"', script_content)
            for hi_res, large in matches:
                hi_res, large = hi_res.strip('"'), large.strip('"')
                image_urls.append(hi_res if hi_res != 'null' else large)
            break
    return image_urls

def save_images(image_urls, asin, save_dir):
    """Download and save images from the extracted URLs."""
    for idx, url in enumerate(image_urls, 1):
        try:
            response = requests.get(url)
            response.raise_for_status()
            file_path = os.path.join(save_dir, f'{asin}_{idx}.jpg')
            with open(file_path, 'wb') as file:
                file.write(response.content)
        except requests.exceptions.RequestException as e:
            print(f"Error downloading {url}: {e}")

def process_single_asin(asin, countries, base_save_dir):
    """Process a single ASIN for all selected countries."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    print(f'Processing ASIN: {asin}')
    
    for country in countries:
        country_code = country[0]
        country_save_dir = os.path.join(base_save_dir, f'images_{country_code}')
        os.makedirs(country_save_dir, exist_ok=True)
        
        image_urls = extract_image_urls(driver, asin, country)
        if image_urls:
            save_images(image_urls, asin, country_save_dir)
            for url in image_urls:
                print(url)
        else:
            print(f"No images found for {asin} in country {country_code}")
    
    driver.quit()

def process_asins(file_path, countries, save_dir, progress_bar, total_asins):
    """Process all ASINs in the input file."""
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        with open(file_path, 'r') as file:
            asins = [line.strip() for line in file.readlines()]

        for asin in asins:
            futures.append(executor.submit(process_single_asin, asin, countries, save_dir))

        for index, future in enumerate(as_completed(futures), start=1):
            try:
                future.result()  # Get the result of the future
            except Exception as e:
                print(f"Error processing ASIN: {asin} - {e}")

            # Update progress bar
            progress_bar['value'] = (index / total_asins) * 100
            root.update_idletasks()

# GUI functions
def select_file():
    """Open file dialog to select a file."""
    file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
    file_label.config(text=file_path)

def select_directory():
    """Open directory dialog to select a save directory."""
    directory_path = filedialog.askdirectory()
    directory_label.config(text=directory_path)

def run():
    """Run the main process."""
    file_path = file_label.cget("text")
    save_dir = directory_label.cget("text")
    
    if not file_path or not save_dir:
        messagebox.showerror("Error", "Please select both a file and a save directory.")
        return

    selected_indices = country_menu.curselection()
    selected_countries = [COUNTRY_OPTIONS[list(COUNTRY_OPTIONS.keys())[i]] for i in selected_indices]

    if not selected_countries:
        messagebox.showerror("Error", "Please select at least one country.")
        return

    try:
        with open(file_path, 'r') as file:
            total_asins = len(file.readlines())
    except FileNotFoundError:
        messagebox.showerror("Error", f"File not found: {file_path}")
        return
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read file: {e}")
        return

    # Start the task in a separate thread
    threading.Thread(target=process_asins, args=(file_path, selected_countries, save_dir, progress_bar, total_asins)).start()

# GUI setup
root = tk.Tk()
root.title("Amazon Image Downloader")
root.resizable(False, False)

font_style = ("Cascadia Mono", 10)

# Title
tk.Label(root, text="amazonImageDownloader", font=("Cascadia Mono", 16, 'bold')).grid(row=0, column=0, sticky="w")

# Marketplace Section
tk.Label(root, text="Marketplace", font=font_style).grid(row=1, column=0, sticky="w")
country_menu = tk.Listbox(root, selectmode='multiple', font=font_style)
for country in COUNTRY_OPTIONS.keys():
    country_menu.insert(tk.END, country)
country_menu.grid(row=2, column=0, sticky="ew")

# ASINs Section
tk.Label(root, text="ASINs", font=font_style).grid(row=3, column=0, sticky="w")
file_label = tk.Label(root, text="No file selected", font=font_style)
file_label.grid(row=4, column=0, sticky="ew")
tk.Button(root, text="Select File", command=select_file, font=font_style).grid(row=5, column=0, sticky="ew")

# Save Directory Section
tk.Label(root, text="Save Directory", font=font_style).grid(row=6, column=0, sticky="w")
directory_label = tk.Label(root, text="No directory selected", font=font_style)
directory_label.grid(row=7, column=0, sticky="ew")
tk.Button(root, text="Select Directory", command=select_directory, font=font_style).grid(row=8, column=0, sticky="ew")

# Run Button
tk.Button(root, text="Run", command=run, font=font_style).grid(row=9, column=0)

# Progress Bar
progress_bar = ttk.Progressbar(root, orient=tk.HORIZONTAL, mode='determinate')
progress_bar.grid(row=10, column=0, sticky="ew")

root.grid_columnconfigure(0, weight=1)  # Ensure the column stretches with window size

root.mainloop()
