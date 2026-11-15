#import libraries
import csv
from pathlib import Path #for working with file/folder locations
from urllib.parse import urlparse, urljoin  #breaks down URL into its components (scheme,domain,path), urljoin turns loc to complete url
from urllib.robotparser import RobotFileParser  #interprets robots.txt rules 

import requests #for retrieving info from webpages
from bs4 import BeautifulSoup #for interpreting thhe HTML

import time #for waiting between requests

import json    #for saving dictionaries as JSON
from datetime import date   #for retrieving date related info


#defined file paths
sources_file = Path("sources/sources.csv")
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

#this function is for retrieving all sources listed in sources.csv
def get_all_sources():
    all_sources = []

    with open(sources_file, mode = "r", encoding = "utf-8-sig", newline = "") as file:
        reader = csv.DictReader(file)

        #iterate every row in sources.csv, add records to the list
        #different from previous function because it doensn't only look for "Registrar"
        for row in reader:
            all_sources.append(row)
    return all_sources

#this function consrtucts a url for the robots.txt file for a webpage
def get_robots_url(url):
    parsed_url = urlparse(url) #separates the passed url into its components

    #make sure url uses https and has a hostname
    if parsed_url.scheme != "https" or not parsed_url.hostname:
        return None

    #create the robot.txt url 
    robots_url = f"https://{parsed_url.hostname}/robots.txt"

    return robots_url

#this is a helper function that organizes the downloaded resources into folders based on their category
def get_output_dir(source):
    #get the category of the source
    category = source["category"]

    #covert category name to folder frindly name
    folder_name = category.lower().replace(" ", "_")

    #create output folder path
    output_path = Path("data/raw") / folder_name
    return output_path

#this function checks the robots.txt file for each source
def check_robots(url):
    parsed_url = urlparse(url) #parse the url/separate it into its components

    #handle urls that are not https or dont belong to the registrar 
    if parsed_url.scheme != "https" or not parsed_url.hostname: 
        print("Skipping invalid or non-HTTPS URL.")
        return False

    #only process the urls listed in the csv file
    approved_urls = {
        s["url"] for s in get_all_sources()
    }

    if url not in approved_urls:
        print("Skipping URL not in sources.csv")
        return False
    
    #stores the robots.txt file for the website
    robots_url = get_robots_url(url)

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
            redirect_location = res.headers.get("Location", "")
            redirect_url = urljoin(robots_url, redirect_location)

            #handle the verified missing file redirect
            missing_robots_redirects = {
                "https://registrar.uwo.ca/404.html",
                "https://www.ssc.uwo.ca/404bssc.html"
            }
            if(res.status_code == 302 and redirect_url in missing_robots_redirects):
                print("Registrar robots.txt redirects to known missing file page")
                return True
            print(f"Unexpected robots.txt redirect: {redirect_url}")
            return False

        #handle other unexpected responses
        if res.status_code != 200:
            print(f"Could not verify robots.txt. HTTP status: {res.status_code}")
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

        #determine output dir for download
        source_output_dir = get_output_dir(source)
        source_output_dir.mkdir(parents = True, exist_ok = True) #create dir if it doesnt exist
        output_file = source_output_dir / f"{source_id}.html"
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
    sources = get_all_sources()
    print(f"Found {len(sources)} sources.")

    #keep track of results
    successful = 0
    skipped = 0
    already_saved = 0 #counter to prevent duplicate downloads

    #iterate through each record
    for s in sources:
        source_id = s["source_id"]
        print(f"\nProcessing {source_id}: {s['notes']}")

        #preview without makiing req's
        if preview:
            print(f"Would process: {s['url']}")
            continue #since were jsut previewing we wont download the html yet, if in preview mode skip the rest and move to next record

        #has the source already been downloaded?
        source_output_dir = get_output_dir(s)
        html_file = source_output_dir / f"{source_id}.html"
        metadata_file = source_output_dir/ f"{source_id}.json"

        #skip already downloaded sources
        if html_file.exists() and metadata_file.exists():
            print(f"Skipping {source_id}: file already exists.")
            already_saved += 1
            continue #move to next iteration (skip download)

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
        print(f"Already saved: {already_saved}")
        print(f"Skipped: {skipped}")       


#testing the preview mode of the scraper
if __name__ == "__main__":
    run_scraper(preview = True)

