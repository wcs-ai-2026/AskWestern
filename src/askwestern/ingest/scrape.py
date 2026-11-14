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

from tempfile import TemporaryDirectory #creates folder for temp work (testin metadata)


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

"""test get_registrar_sources
    if __name__ == "__main__":
    sources = get_registrar_source()
    print(f"Found {len(sources)} Registrar sources:\n")
    for s in sources:
        print(f"ID: {s['source_id']}")        
        print(f"Name: {s['notes']}")
        print(f"URL: {s['url']}")
        print()
"""

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

        if res.status_code != 200:
            print(f"Could not verify robots.txt. HTTP status: {res.status_code}")

            if res.status_code in [301, 302, 307, 308]:
                redirect_url = res.headers.get("Location")
                print(f"Redirect dest: {redirect_url}")
            print("Skipping automated collection until permissions are verified")
            return False    
            #print("Could not verify robots.txt. Skipping")
            #return False

            

        #read the rules iin the file
        robots = RobotFileParser()
        robots.parse(res.text.splitlines())


        # true: rules allow access, false: not allowed to access
        return robots.can_fetch(user_agent, url)

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

# the testing below returned "could not verify" with status code 302 {page was getting redirected to a 404 not found page}
# so i am adding an extract text function to test HTML extraction using the seed files
#testing the robots fucntion
#if __name__ == '__main__':
#    sources = get_registrar_source()
#    first_source = sources[0]
#    print(f"Checking: {first_source['notes']}")
#    allowed = check_robots(first_source["url"])

#   if allowed:
#        print("Robots.txt allows this page for the scraper.")
#    else:
#        print("Automated access is not allowed.")    


#test for the extract function with one of the existing html seed pages
#if __name__ == "__main__":
#    seed_file = Path("data/seed/REG001.html")
#    with open(seed_file, mode = "r", encoding = "utf-8") as file:
#        html = file.read()

#    extracted_text = extract_text(html)
#    print("text: ")
#    print(extracted_text[:1000])   

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

#testing the metadata function
#if __name__ == "__main__":
#    sources = get_registrar_source()
#    first_source = sources[0]
#    seed_file = Path("data/seed/REG001.html")
#    html = seed_file.read_text(encoding = "utf-8")

#    extracted_text = extract_text(html)
#    metadata = create_metadata(first_source)
#    print("source metadata: ")

#    for key, value in metadata.items():
#        print(f"{key}: {value}")

#    print(f"\ntext length: {len(extracted_text)}")    

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

# testing the download fucntion
#if __name__ == "__main__":
#    sources = get_registrar_source()
#    first_source = sources[0]
#    print(f"Attempting to download: {first_source['notes']}")
#    success = download_page(first_source)

#    if success: 
#        print("download successful")
#    else:
#        print("download unsuccessful")    

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


#testing metadata function (DONT TEST YET THIS WILL CREATE A JSON)
#if __name__ == "__main__":
#    sources = get_registrar_source()
#    first_source = sources[0]

    #rhis will create a temp folder 
#    with TemporaryDirectory() as temp_dir:
#        test_file = Path(temp_dir) / "REG001.html" #this is a temp file path in the temp dir
#        save_scrape_metadata(first_source, test_file)
#        metadata_file = test_file.with_suffix(".json")
#        saved_metadata = json.loads(metadata_file.read_text(encoding = "utf-8")) #converts json text back to python
#        print("\nSaved metadata:")

#        for key, value in saved_metadata.items():
#            print(f"{key}: {value}")

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