import requests
import os
import re
from urllib.parse import quote


# COMMON FUNCTIONS
# ============================================================

def clean_filename(title):
    """
    Converts a paper title into a safe filename.
    """
    title = re.sub(r'[<>:"/\\|?*]', '', title)
    title = title[:100]
    return title.strip() + ".pdf"


def download_paper(pdf_url, title):
    """
    Downloads a PDF from a publicly accessible PDF URL.
    """
    if not pdf_url:
        print("\nNo downloadable PDF link was found.")
        return

    try:
        print("\nDownloading paper...")

        response = requests.get(
            pdf_url,
            timeout=30,
            stream=True,
            headers={
                "User-Agent": "ResearchPaperAPI/1.0"
            }
        )

        response.raise_for_status()

        filename = clean_filename(title)

        with open(filename, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)

        print(f"\nPaper downloaded successfully:")
        print(filename)

    except requests.exceptions.RequestException as e:
        print("\nDownload failed.")
        print("Error:", e)


def display_papers(papers):
    """
    Displays research papers in a simple numbered format.
    """

    if not papers:
        print("\nNo papers found.")
        return

    print("\n" + "=" * 80)
    print("RESEARCH PAPERS")
    print("=" * 80)

    for i, paper in enumerate(papers, start=1):

        print(f"\n[{i}] {paper['title']}")
        print("Authors :", paper.get("authors", "Unknown"))
        print("Year    :", paper.get("year", "Unknown"))
        print("Source  :", paper.get("source", "Unknown"))

        if paper.get("pdf_url"):
            print("PDF     :", paper["pdf_url"])
        else:
            print("PDF     : Not available")

    print("=" * 80)


def choose_paper(papers):
    """
    Allows the user to select a paper and optionally download it.
    """

    if not papers:
        return

    try:
        choice = int(input("\nEnter paper number to download (0 to go back): "))

        if choice == 0:
            return

        if choice < 1 or choice > len(papers):
            print("Invalid paper number.")
            return

        selected = papers[choice - 1]

        print("\nSelected paper:")
        print(selected["title"])

        if not selected.get("pdf_url"):
            print("\nNo public PDF is available for this result.")
            print("Paper link:", selected.get("url", "Not available"))
            return

        download_paper(
            selected["pdf_url"],
            selected["title"]
        )

    except ValueError:
        print("Please enter a valid number.")



# 1. OPENALEX API
# ============================================================

def search_openalex(query):
    """
    Searches research papers using OpenAlex API.
    """

    url = "https://api.openalex.org/works"

    params = {
        "search": query,
        "per-page": 5
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        papers = []

        for item in data.get("results", []):

            authors = []

            for author in item.get("authorships", []):
                author_name = author.get("author", {}).get("display_name")

                if author_name:
                    authors.append(author_name)

            pdf_url = None

            # Try OpenAlex primary location
            primary_location = item.get("primary_location")

            if primary_location:
                source = primary_location.get("source")

                if source:
                    pass

                pdf_url = primary_location.get("pdf_url")

            # Try Open Access location
            if not pdf_url:
                open_access = item.get("open_access")

                if open_access:
                    pdf_url = open_access.get("oa_url")

            papers.append({
                "title": item.get("title", "Unknown"),
                "authors": ", ".join(authors),
                "year": item.get("publication_year", "Unknown"),
                "pdf_url": pdf_url,
                "url": item.get("doi") or item.get("id"),
                "source": "OpenAlex"
            })

        return papers

    except requests.exceptions.RequestException as e:
        print("OpenAlex API error:", e)
        return []


# 2. CROSSREF API
# ============================================================

def search_crossref(query):
    """
    Searches research papers using Crossref API.
    """

    url = "https://api.crossref.org/works"

    params = {
        "query.title": query,
        "rows": 5
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        papers = []

        for item in data["message"]["items"]:

            authors = []

            for author in item.get("author", []):
                name = (
                    author.get("given", "") +
                    " " +
                    author.get("family", "")
                ).strip()

                if name:
                    authors.append(name)

            pdf_url = None

            # Crossref sometimes provides links
            for link in item.get("link", []):
                content_type = link.get("content-type", "")

                if "pdf" in content_type.lower():
                    pdf_url = link.get("URL")
                    break

            # DOI is normally the safest general paper link
            doi_url = item.get("URL")

            year = "Unknown"

            if "published-print" in item:
                date_parts = item["published-print"].get(
                    "date-parts",
                    []
                )

                if date_parts:
                    year = date_parts[0][0]

            elif "published-online" in item:
                date_parts = item["published-online"].get(
                    "date-parts",
                    []
                )

                if date_parts:
                    year = date_parts[0][0]

            papers.append({
                "title": item.get("title", ["Unknown"])[0],
                "authors": ", ".join(authors),
                "year": year,
                "pdf_url": pdf_url,
                "url": doi_url,
                "source": "Crossref"
            })

        return papers

    except requests.exceptions.RequestException as e:
        print("Crossref API error:", e)
        return []


# 3. ARXIV API
# ============================================================

def search_arxiv(query):
    """
    Searches research papers using arXiv API.
    """

    url = "https://export.arxiv.org/api/query"

    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": 5
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        xml_text = response.text

        # Basic XML parsing
        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml_text)

        namespace = {
            "atom": "http://www.w3.org/2005/Atom"
        }

        papers = []

        for entry in root.findall("atom:entry", namespace):

            title = entry.find(
                "atom:title",
                namespace
            )

            published = entry.find(
                "atom:published",
                namespace
            )

            authors = []

            for author in entry.findall(
                "atom:author",
                namespace
            ):
                name = author.find(
                    "atom:name",
                    namespace
                )

                if name is not None:
                    authors.append(name.text)

            paper_url = None
            pdf_url = None

            for link in entry.findall(
                "atom:link",
                namespace
            ):

                link_type = link.get("type")
                link_href = link.get("href")

                if link_type == "application/pdf":
                    pdf_url = link_href

                elif link.get("rel") == "alternate":
                    paper_url = link_href

            year = "Unknown"

            if published is not None:
                year = published.text[:4]

            papers.append({
                "title": title.text.strip() if title is not None else "Unknown",
                "authors": ", ".join(authors),
                "year": year,
                "pdf_url": pdf_url,
                "url": paper_url,
                "source": "arXiv"
            })

        return papers

    except requests.exceptions.RequestException as e:
        print("arXiv API error:", e)
        return []

    except ET.ParseError as e:
        print("Could not read arXiv response.")
        print(e)
        return []

# 4. SEMANTIC SCHOLAR API
# ============================================================

def search_semantic_scholar(query):
    """
    Searches research papers using Semantic Scholar API.
    """

    url = "https://api.semanticscholar.org/graph/v1/paper/search"

    params = {
        "query": query,
        "limit": 5,
        "fields": (
            "title,authors,year,url,"
            "openAccessPdf"
        )
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        papers = []

        for item in data.get("data", []):

            authors = []

            for author in item.get("authors", []):
                if author.get("name"):
                    authors.append(author["name"])

            pdf_url = None

            open_access = item.get("openAccessPdf")

            if open_access:
                pdf_url = open_access.get("url")

            papers.append({
                "title": item.get("title", "Unknown"),
                "authors": ", ".join(authors),
                "year": item.get("year", "Unknown"),
                "pdf_url": pdf_url,
                "url": item.get("url"),
                "source": "Semantic Scholar"
            })

        return papers

    except requests.exceptions.RequestException as e:
        print("Semantic Scholar API error:", e)
        return []

# 5. EUROPE PMC API
# ============================================================

def search_europe_pmc(query):
    """
    Searches biomedical and life-science research papers
    using Europe PMC API.
    """

    url = (
        "https://www.ebi.ac.uk/europepmc/webservices/"
        "rest/search"
    )

    params = {
        "query": query,
        "format": "json",
        "pageSize": 5
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        papers = []

        for item in data.get("resultList", {}).get(
            "result",
            []
        ):

            authors = item.get(
                "authorString",
                "Unknown"
            )

            year = item.get(
                "pubYear",
                "Unknown"
            )

            pmcid = item.get("pmcid")

            pdf_url = None

            # Europe PMC full-text papers can be accessed
            # through their PMC record when available.
            if pmcid:
                pdf_url = (
                    "https://europepmc.org/articles/"
                    + pmcid
                )

            paper_url = None

            if item.get("pmid"):
                paper_url = (
                    "https://pubmed.ncbi.nlm.nih.gov/"
                    + str(item["pmid"])
                )

            papers.append({
                "title": item.get(
                    "title",
                    "Unknown"
                ),
                "authors": authors,
                "year": year,
                "pdf_url": pdf_url,
                "url": paper_url,
                "source": "Europe PMC"
            })

        return papers

    except requests.exceptions.RequestException as e:
        print("Europe PMC API error:", e)
        return []


def show_menu():
    """
    Displays the API selection menu.
    """

    print("\n")
    print("=" * 60)
    print("       RESEARCH PAPER API EXPLORER")
    print("=" * 60)

    print("\nSelect a research paper API:")

    print("1. OpenAlex")
    print("2. Crossref")
    print("3. arXiv")
    print("4. Semantic Scholar")
    print("5. Europe PMC")
    print("0. Exit")



# MAIN PROGRAM
# ============================================================

def main():

    while True:

        show_menu()

        choice = input(
            "\nEnter your choice: "
        ).strip()

        if choice == "0":
            print("\nProgram ended.")
            break

        
        # Select API
        # ----------------------------------------------------

        api_functions = {
            "1": search_openalex,
            "2": search_crossref,
            "3": search_arxiv,
            "4": search_semantic_scholar,
            "5": search_europe_pmc
        }

        if choice not in api_functions:
            print("\nInvalid choice.")
            continue

   
        # User research query

        query = input(
            "\nEnter research topic, keyword, "
            "author name or paper title: "
        ).strip()

        if not query:
            print("Search query cannot be empty.")
            continue

        print("\nSearching...")
        print("Query:", query)

       

        search_function = api_functions[choice]

        papers = search_function(query)


        display_papers(papers)



        if papers:
            choose_paper(papers)



if __name__ == "__main__":
    main()
