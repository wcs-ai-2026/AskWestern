import hashlib #using SHA-256 to create fingerprint for each chunk
import re
from bs4 import BeautifulSoup

#what we will be removing
UNWANTED_TAGS = [
    "script",
    "style",
    "nav",
    "footer",
    "header",
    "noscript",
    "aside",
]

#common names for menus, banners, and other repeated interface elements
UNWANTED_NAMES = re.compile(
    r"(^|[-_\s])(nav|navbar|menu|footer|cookie|"
    r"breadcrumb|sidebar|site-banner|promo-banner|"
    r"announcement-banner)([-_\s]|$)",
    re.IGNORECASE,
)

#extract important info, remove clutter
def clean_html(html):

    soup = BeautifulSoup(html, "html.parser")

    #remove unnecessary html tags
    for e in soup(UNWANTED_TAGS):
        e.decompose()

    #remove elements by class or ID
    for e in list(soup.find_all(True)):
        if e.parent is None:
            continue

        classes = " ".join(e.get("class", []))
        e_id = e.get("id", "")
        role = e.get("role", "")
        names = f"{classes} {e_id}"

        if(UNWANTED_NAMES.search(names) or role in {"navigation", "banner", "contentinfo"}):
            e.decompose()

    #remove calendar filtering panels found during testing
    #only remove it if its heading identifies it as a filter
    for panel in list(soup.select("div.panel")):
        heading = panel.select_one(".panel-heading .panel-title") #these are the specific headings that identify it as a filter
        if heading is None:
            continue
        heading_text = heading.get_text(" ", strip=True)
        if heading_text.casefold().startswith("filter by:"):
            panel.decompose()

    #remove the academic calendar policy navigation sidebar (found in testing)
    for heading in list(soup.select("h3.policyTitleSideMenu")):
        if heading.get_text(" ", strip=True).casefold() == "policy categories":
            sidebar = heading.find_parent("div", class_="col-md-3")

            if sidebar is not None:
                sidebar.decompose()

    #remove the course navigation button (found in testing)
    for link in list(soup.select("a.btn.btn-info.novecento")):
        if link.get_text(" ", strip=True).casefold() == "or search by courses":
            link.decompose()

    #remove the facult/staff search interface
    for search_panel in list(soup.select("div#ribbon-directory")):
        search_panel.decompose()
        
    #main contnt of the page
    main = soup.find("main")

    if main is None: 
        main = soup.select_one("div.main-content")

    content = main if main else soup.body

    if content is None:
        return ""

    #convert html to readable text
    text = content.get_text(separator = " ", strip = True)
    return re.sub(r"\s+", " ", text).strip()


#remove identical chucks but keep their order
def deduplicate_chunks(chunks):
    unique_chunks = []
    seen = set()

    for c in chunks:
        normalized = re.sub(r"\s+", " ", c).strip()

        if not normalized:
            continue

        #hash the normalized text to identify duplicates
        fingerprint = hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest()

        if fingerprint in seen:
            continue

        seen.add(fingerprint)
        unique_chunks.append(normalized)

    return unique_chunks