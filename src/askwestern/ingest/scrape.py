#import libraries
import csv
from pathlib import Path #for working with file/folder locations
from urllib.parse import urlparse  #breaks down URL into its components (scheme,domain,path)
from urllib.robotparser import RobotFileParser  #interprets robots.txt rules 

import requests #for retrieving info from webpages
from bs4 import BeautifulSoup #for interpreting thhe HTML

import time #for waiting between requests

import json    #for saving dictionaries as JSON
from datetime import date   #for retrieving date related info


#defined file paths
sources_file = Path("sources/sources.csv")
output_dir = Path("data/raw/registrar")
user_agent = "WCS-AskWestern/1.0"

# this function gets the regstrar sources from the csv file
def get_registrar_source():
    registrar_sources = []

    #open the sources file, read it, close the file when finished (with)
    with open(sources_file, mode = "r", encoding = "utf-8-sig", newline = "") as file: 
        reader = csv.DictReader(file) #read csv with column names

        #iterate over every row, check if category is Registrar, add proper records to the list
        for row in reader: 
            if row["category"] == "Registrar":
                registrar_sources.append(row)

    return registrar_sources    

#this function checks the robots.txt file for each source
def check_robots(url):
    parsed_url = urlparse(url) #parse the url/separate it into its components

    #handle urls that are not https or dont belong to the registrar 
    if parsed_url.scheme != "https" or parsed_url.hostname != "registrar.uwo.ca": 
        print("Skipping URL outside the approved Registrar website.")
        return False

    #stores the robots.txt file for the website
    robots_url = "https://registrar.uwo.ca/robots.txt"

    try:
        #request the robots.txt from uwo server
        res = requests.get(
            robots_url,
            headers = {"User-Agent": user_agent},
            timeout = 15,
            allow_redirects = False
        )

        #if the robots.txt file is missing
        if res.status_code in [404, 410]:
            print("Robots.txt does not exist.")
            return True

        #handle other redirects
        if res.status_code in [301, 302, 307, 308]:
            redirect_url = res.headers.get("Location")
            print(f"Robots.txt redirects to: {redirect_url}")
            print("Redirect requires verification before scraping.")
            return False

        #read robots.txt rules
        robots = RobotFileParser()
        robots.parse(res.text.splitlines())

        #check if the scraper is allowed to access page
        allowed = robots.can_fetch(user_agent, url)
        if allowed:
            print("Robots.txt allows scraping")
        else:
            print("Robots.txt does not allow scraping")

        return allowed
    except requests.RequestException as error:
        print(f"Error checking robots.txt: {error}")
        return False

#this function extracts readable informaton from HTML (aka our seed pages)
def extract_text(html):
    #interprets the passed html using python's built in parser
    soup = BeautifulSoup(html, "html.parser")

    #find and remove the html elements
    for i in soup(["script", "style", "nav", "footer"]):
        i.decompose()

    #find the main content section
    main_content = soup.select_one("div.main-content")

    #use main content when available
    if main_content:
        text = main_content.get_text(separator = " ", strip = True)
    else: 
        text = soup.get_text(separator = " ", strip = True)        

    #extract the remaining text, separator adds space between the text elements, strip removes whitespace
    #text = soup.get_text(separator = " ", strip = True)
    return text    

#this function creates metadata for a seed page
def create_metadata(source):
    #dictionary from sources.csv
    metadata = {
        "source_id": source["source_id"],
        "source_url": source["url"],
        "title": source["notes"],
        "collected_on": "2026-11-09",
        "source_type": "manual"
    }

    return metadata

#this function downloads and saves approved registrar webpages
def download_page(source):
    #extract the source info
    source_id = source["source_id"]
    url = source["url"]

    #executed if webpage does not allow scraping
    if not check_robots(url):
        print(f"Skipping {source_id}: scraping permission not verified")
        return False

    #wait before making another request
    time.sleep(1.5)

    try:
        #this sends an HTTP GET request
        res = requests.get(
            url,
            headers = {"User-Agent": user_agent},
            timeout = 15,
            allow_redirects = False
        )

        #this ensures we don't folllow redirects automatically
        if 300 <= res.status_code < 400:
            print(f"Skipping {source_id}: redirect requires review.")
            return False

        #raise error for failed HTTP responses
        res.raise_for_status()

        #response must contain html
        content_type = res.headers.get("Content-Type", "")

        if "text/html" not in content_type.lower():
            print(f"Skipping {source_id}: response not HTML.")
            return False

        #create output folder and file
        output_dir.mkdir(parents = True, exist_ok = True)
        output_file = output_dir / f"{source_id}.html"

        #save the original html
        output_file.write_bytes(res.content)

        #save source metadata
        save_scrape_metadata(source, output_file)

        print(f"Successfully saved {source_id} to {output_file}")
        return True

    except requests.RequestException as error:
        print(f"Error downloading {source_id}: {error}")
        return False

#save metadata for automatically downloaded webpage
def save_scrape_metadata(source, output_file):
    #the metadata dictionary
    metadata = {
        "source_id": source["source_id"],
        "source_url": source["url"],
        "title": source["notes"],
        "collected_on": date.today().isoformat(),
        "source_type": "html" #diff from other metadata function cz this one saves html automatically (not from seed page)
    }

    metadata_file = output_file.with_suffix(".json") #json file name
    metadata_file.write_text(
        json.dumps(metadata, indent = 4), #converts the dictionary into JSON text
        encoding = "utf-8"
    )

    print(f"Saved metadata to: {metadata_file}")

# this is the MAIN scraper function
def run_scraper(preview = True):
    sources = get_registrar_source()
    print(f"Found {len(sources)} registrar sources.")

    #keep track of results
    successful = 0
    skipped = 0

    #iterate through each record
    for s in sources:
        source_id = s["source_id"]
        print(f"\nProcessing {source_id}: {s['notes']}")

        #preview without makiing req's
        if preview:
            print(f"Would process: {s['url']}")
            continue #since were jsut previewing we wont download the html yet, if in preview mode skip the rest and move to next record

        #try to download
        success = download_page(s)
        if success:
            successful += 1
        else:
            skipped += 1

        #wait before checking another source
        time.sleep(1.5)
    print("\nScraper Summary:") 
    if preview:
        print(f"Previewed: {len(sources)}")
        print("no webpages downloaded")
    else:
        print(f"Successful downloads: {successful}")
        print(f"Skipped: {skipped}")       


#testing the preview mode of the scraper
if __name__ == "__main__":
    run_scraper(preview = True)