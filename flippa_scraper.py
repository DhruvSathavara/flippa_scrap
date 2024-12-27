import httpx
import asyncio
import random
from selectolax.parser import HTMLParser
from httpx import AsyncHTTPTransport
import os
from dotenv import load_dotenv
from utils import log_ip_address  
# Load environment variables from .env file
load_dotenv()

# Fetch the PROXY_URL from the .env file
PROXY_URL = os.getenv("PROXY_URL")

# List of User-Agent strings for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
]
 
async def fetch_page(client, page_number, retries=3):
    """
    Fetch a page of listings from the Flippa API with retry logic for 429 errors.
    Args:
        client: The HTTPX AsyncClient instance.
        page_number: The page number to fetch.
        retries: Number of retries allowed in case of failure.
    Returns:
        A list of listings from the API response.
    """
    url = "https://flippa.com/search"
    params = {
        "filter[property_type]": "website,fba,saas,ecommerce_store,plugin_and_extension,ai_apps_and_tools,youtube,ios_app,android_app,game,crypto_app,social_media,newsletter,service_and_agency,service,other",
        "filter[revenue_generating]": "T,F",
        "filter[sale_method]": "auction,classified",
        "filter[status]": "open",
        "format": "js",
        "page[number]": page_number,
        "search_template": "most_relevant",
    }

    for attempt in range(1, retries + 1):
        try:
            # Rotate User-Agent
            headers = {
                "Accept": "application/json, text/plain, */*",
                "User-Agent": random.choice(USER_AGENTS),
            }
            # Log the IP address before making the request
            await log_ip_address(client)

            response = await client.get(url, params=params, headers=headers, timeout=20)

            # Handle 429 Too Many Requests
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 10))  # Default to 10 seconds
                print(f"Rate limited. Waiting for {retry_after} seconds before retrying...")
                await asyncio.sleep(retry_after)
                continue  # Retry the request

            response.raise_for_status()  # Raise exception for other HTTP errors
            data = response.json()
            return data.get("results", [])  # Return listings

        except httpx.RequestError as e:
            print(f"Attempt {attempt}/{retries} failed for page {page_number}: {e}")
            if attempt == retries:
                return []  # Return empty list on final failure
            await asyncio.sleep(10)  # Wait before retrying


async def scrape_flippa_links():
    """
    Scrape all Flippa listing links until no more pages are found.
    Combines delays, User-Agent rotation, and rate-limit handling.
    Returns:
        A list of detail page URLs.
    """
    all_links = []
    page_number = 1
    transport = AsyncHTTPTransport(proxy=PROXY_URL)
    async with httpx.AsyncClient(transport=transport) as client:
        while True:

            print(f"Fetching page {page_number}...")
            listings = await fetch_page(client, page_number)
            if not listings:  # Stop if no listings are found
                print(f"No listings found on page {page_number}. Stopping.")
                break

            # Extract only the detail page links
            links = [listing.get("listing_url") for listing in listings if listing.get("listing_url")]
            all_links.extend(links)

            print(f"Scraped {len(links)} links from page {page_number}.")
            page_number += 1

            # Add a 3-second delay between requests
            await asyncio.sleep(3)

    return all_links


async def main():
    """
    Main function to scrape Flippa and display the detail page links.
    """
    links = await scrape_flippa_links()

    print("\nScraped Links:")
    for idx, link in enumerate(links, start=1):
        print(f"{idx}. {link}")

    # Save to a file ( for testing)
    with open("flippa_links.txt", "w") as file:
        for link in links:
            file.write(f"{link}\n")
    print("\nLinks saved to flippa_links.txt")
 
    #  from here it is the detail page  

async def scrape_detail_page(url):
    """
    Scrape a detail page using the proxy.
    """
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
    }

    # Use the proxy transport for the detail page
    transport = AsyncHTTPTransport(proxy=PROXY_URL)

    async with httpx.AsyncClient(transport=transport, follow_redirects=True) as client:
        try:
            # Log the IP address before making the request (optional for debugging)
            await log_ip_address(client)

            response = await client.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            html = HTMLParser(response.text)

            details = {}
            additional_info = {}

            details["source_url"] = url

            # Get title
            title_element = html.css_first(".Onboarding__content h2")
            if title_element:
                details["title"] = title_element.text(strip=True)

            # Get business type (industry)
            industry_element = html.css_first(".Onboarding__content p")
            if industry_element:
                details["industry"] = [industry_element.text(strip=True)]

            # Get tags (additional industries)
            tags_container = html.css_first(".tw-mb-8.tw-flex.tw-flex-wrap")
            if tags_container:
                tags = tags_container.css("a")
                if tags:
                    for tag in tags:
                        industry = tag.text(strip=True)
                        if industry and industry.lower() not in [
                            "sponsored",
                            "buy now",
                            "confidential",
                        ]:
                            details.setdefault("industry", []).append(industry)

            # Get business description
            description_element = html.css_first(".pg-1.mb-3")
            if description_element:
                details["description"] = description_element.text(strip=True)

            # Get asking price
            price_element_box = html.css_first(".bid-box-price")
            if price_element_box:
                price_element = price_element_box.css_first("h5")
                if price_element:
                    details["asking_price"] = price_element.text(strip=True)

            # Get 'about business'
            about_business_element = html.css_first("div[data-controller='toggle-class']")
            if about_business_element:
                additional_info["about_business"] = about_business_element.text(strip=True)

            # Get additional info (e.g., site age, profit margin, etc.)
            additional_info_elements = html.css("#properties-summary .d-flex.Onboarding__properties-item")
            for info_element in additional_info_elements:
                label_element = info_element.css_first(".pg-3")
                value_element = info_element.css_first(".pg-1")
                if label_element and value_element:
                    label = label_element.text(strip=True)
                    value = value_element.text(strip=True)
                    if label.lower() in ["site age", "app age"]:
                        details["business_age"] = value
                    else:
                        additional_info[label] = value

            # Add additional info to details
            details["additional_info"] = additional_info

            # Save the details to a file (optional for debugging)
            with open("flippa_details.txt", "w") as file:
                file.write(f"{details}\n")
            print("Scraped details:", details)
            return details

        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None


if __name__ == "__main__":
    # asyncio.run(main())
    asyncio.run(scrape_detail_page("https://flippa.com/11634071"))