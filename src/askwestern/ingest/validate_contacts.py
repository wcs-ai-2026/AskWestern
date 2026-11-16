"""this is script is to validate the following attributes of the sontacts.jsonl file:
        must have one obj per line
        each obj has 8 fields
        each field contains correct data type
        contact IDs are unique and have the proper naming format
        urls must be https
        dates have proper format
        student central fallback exists
"""

import json
import re
from pathlib import Path
from datetime import date
from urllib.parse import urlparse

#path to contacts.jsonl
contacts_file = Path("data/processed/contacts.jsonl")

required_fields = {
    "contact_id": str,
    "office": str,
    "handles": list,
    "faculty": str,
    "contact_page": str,
    "email": str,
    "phone": str,
    "collected_on": str
}

#this function loads the records in the contacts fike
def load_contacts(): 
    contacts = []

    #read the file and add the records to the list
    with open (contacts_file, mode = "r", encoding = "utf-8") as file:
        for line_number, line in enumerate(file, start = 1): #helps track the line numbers in the file
            #skip empty lines
            if not line.strip():
                print(f"empty line found at line {line_number}")
                continue

            #convest json line to python dictionary 
            try: 
                contact = json.loads(line)
                contacts.append(contact)

            except json.JSONDecodeError as error:
                print(f"Invalid JSON on line {line_number}: {error}")
                return None

    return contacts

#this function validates the fields in each record
def validate_contacts(contacts):
    errors = []
    seen_ids = set() #to keep track of the ids

    #iterate through each contact
    for c in contacts:
        #check that the contact is a dict
        if not isinstance(c, dict):
            errors.append("contact must be a dictionary.")
            continue

        # Check that the record contains exactly the required fields
        extra_fields = set(c.keys()) - set(required_fields.keys())

        if extra_fields:
            errors.append(f"Unexpected fields for {c.get('contact_id')}: {extra_fields}")
            
        #check all the required fields
        for field, expected_type in required_fields.items():
            #check if the field exists in the record
            if field not in c:
                errors.append(f"Missing required field: {field}")
                continue

            #check if the field is correct type
            if not isinstance(c[field], expected_type):
                errors.append(f"Incorrect field type: {field}")

        c_id = c.get("contact_id") #extract the id of the record

        #checks for duplicates
        if isinstance(c_id, str): 
            if c_id in seen_ids:
                errors.append(f"Duplicate contact ID: {c_id}")
            else:
                seen_ids.add(c_id)

        #checks the id formats
        if isinstance(c_id, str):
            if not re.fullmatch(r"[a-z]+(?:-[a-z]+)*", c_id):
                errors.append(f"Invalid contact ID format: {c_id}")

        #extract the handles
        handles = c.get("handles")

        #check that the handles field is not empty and is a list
        if isinstance(handles, list):
            if not handles:
                errors.append(f"Empty handles list: {c_id}")

            for i in handles:
                if not isinstance(i, str) or not i.strip():
                    errors.append(f"Invalid entry for handles: {c_id}")

        #check proper date format YYYY-MM-DD
        collected_on = c.get("collected_on")

        if isinstance(collected_on, str):
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", collected_on):
                errors.append(f"invalid date format: {c_id}")
            else: #check the date actually exists
                try: 
                    date.fromisoformat(collected_on)
                except ValueError:
                    errors.append(f"Invlaid collection date for: {c_id}")

        #checks the url is https and has a hostname
        c_page = c.get("contact_page")

        if isinstance(c_page, str):
            parsed_url = urlparse(c_page)
            if parsed_url.scheme != "https" or not parsed_url.hostname:
                errors.append(f"Invalid URL: {c_id}")
    #this section of the code checks that the fallback contact exists
    c_ids = {
        c["contact_id"]
        for c in contacts
        if isinstance(c, dict)
        and isinstance(c.get("contact_id"), str)
    }

    if "registrar-student-central" not in c_ids:
        errors.append("Missing the fallback contact: registrar-student-central")

    return errors



if __name__ == "__main__":
    contacts = load_contacts()

    if contacts is None: 
        print("failed to load contacts")
        raise SystemExit(1)
    
    
    errors = validate_contacts(contacts)
    if errors:
        print(f"found {len(errors)} errors.")

        for e in errors: 
            print(e)

        raise SystemExit(1)

    else:
        print(f"successfully validated {len(contacts)} contacts.")

