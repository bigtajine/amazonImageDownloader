import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
import requests
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Author: bigtajine
# Script Name: AmazonImageDownloader.py
# Last Modified: 2024-11-20

# Country options for Amazon websites
country_options = {
    "Amazon de": ("de", "de"),
    "Amazon co.uk": ("co.uk", "en"),
    "Amazon com.be": ("com.be", "fr"),
    "Amazon fr": ("fr", "fr"),
    "Amazon es": ("es", "es"),
    "Amazon se": ("se", "sv"),
    "Amazon nl": ("nl", "nl"),
    "Amazon it": ("it", "it"),
    "Amazon pl": ("pl", "pl")
}

def extract_image_urls(driver, asin, country):
    url = f'https://www.amazon.{country[0]}/dp/{asin}?th=1'
    driver.get(url)
    driver.implicitly_wait(10)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    scripts = soup.find_all('script')
    image_urls = []

    for script in scripts:
        script_content = script.string
        if script_content and 'colorImages' in script_content:
            matches = re.findall(r'{"hiRes":(null|"https://m\.media-amazon\.com/images/I/[^\"]*"),"thumb":"https://m\.media-amazon\.com/images/I/[^\"]*","large":"(https://m\.media-amazon\.com/images/I/[^\"]*)"', script_content)
            for hi_res, large in matches:
                hi_res = hi_res.strip('"')
                large = large.strip('"')
                if hi_res != 'null':
                    image_urls.append(hi_res)
                elif large:
                    image_urls.append(large)
            break
    return image_urls

def save_images(image_urls, asin, save_dir):
    for idx, url in enumerate(image_urls, 1):
        response = requests.get(url)
        if response.status_code == 200:
            file_path = os.path.join(save_dir, f'{asin}_{idx}.jpg')
            with open(file_path, 'wb') as f:
                f.write(response.content)

def process_single_asin(asin, countries, base_save_dir):
    # Configure Chrome options
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
            for link in image_urls:
                print(link)
        else:
            print(f"No images found for {asin} in country {country_code}")
    print('-' * 20)
    driver.quit()

def process_asins(file_path, countries, save_dir, progress_bar, total_asins):
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        with open(file_path, 'r') as file:
            asins = [line.strip() for line in file.readlines()]
        
        for asin in asins:
            futures.append(executor.submit(process_single_asin, asin, countries, save_dir))
        
        for index, future in enumerate(as_completed(futures), start=1):
            future.result()
            progress_bar['value'] = (index / total_asins) * 100
            root.update_idletasks()

def select_file():
    file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
    file_label.config(text=file_path)

def select_directory():
    directory_path = filedialog.askdirectory()
    directory_label.config(text=directory_path)

def run():
    file_path = file_label.cget("text")
    save_dir = directory_label.cget("text")
    if not file_path:
        messagebox.showerror("Error", "Please select a file.")
        return

    if not save_dir:
        messagebox.showerror("Error", "Please select a directory.")
        return

    selected_indices = country_menu.curselection()
    selected_countries = [country_options[list(country_options.keys())[i]] for i in selected_indices]

    if not selected_countries:
        messagebox.showerror("Error", "Please select at least one country.")
        return

    with open(file_path, 'r') as file:
        total_asins = len(file.readlines())
    
    process_asins(file_path, selected_countries, save_dir, progress_bar, total_asins)

# Set up GUI
root = tk.Tk()
root.title("AmazonImageDownloader")
root.configure(bg="#E6E6FA")  # Pastel purple background

font_style = ("Arial", 12)

frame = tk.Frame(root, bg="#E6E6FA")
frame.pack(padx=10, pady=10)

country_var = tk.StringVar()

tk.Label(frame, text="Country:", bg="#E6E6FA", fg="black", font=font_style).pack(anchor=tk.W)
country_menu = tk.Listbox(frame, listvariable=country_var, selectmode='multiple', bg="#D8BFD8", fg="black", font=font_style)
for country in country_options.keys():
    country_menu.insert(tk.END, country)
country_menu.pack(fill=tk.X, padx=5, pady=5)

tk.Label(frame, text="ASINs File:", bg="#E6E6FA", fg="black", font=font_style).pack(anchor=tk.W)
file_label = tk.Label(frame, text="No file selected", bg="#F8F8FF", fg="black", font=font_style)
file_label.pack(fill=tk.X, padx=5, pady=5)
select_file_button = tk.Button(frame, text="Select File", command=select_file, bg="#D8BFD8", fg="black", font=font_style)
select_file_button.pack(fill=tk.X, padx=5, pady=5)

tk.Label(frame, text="Save Directory:", bg="#E6E6FA", fg="black", font=font_style).pack(anchor=tk.W)
directory_label = tk.Label(frame, text="No directory selected", bg="#F8F8FF", fg="black", font=font_style)
directory_label.pack(fill=tk.X, padx=5, pady=5)
select_directory_button = tk.Button(frame, text="Select Directory", command=select_directory, bg="#D8BFD8", fg="black", font=font_style)
select_directory_button.pack(fill=tk.X, padx=5, pady=5)

run_button = tk.Button(root, text="Run", command=run, bg="#DDA0DD", fg="black", font=font_style)
run_button.pack(pady=10)

progress_bar = Progressbar(root, orient=tk.HORIZONTAL, length=300, mode='determinate')
progress_bar.pack(pady=10)

root.mainloop()
