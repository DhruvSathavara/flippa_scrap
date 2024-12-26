# business broker script
import asyncio
from typing import List
import json
from httpx import AsyncClient
from selectolax.parser import HTMLParser
from src2.scraper.scraper_utils import get_proxy_settings


async def get_listing_urls(state_url: str, max_retries: int = 3) -> List[str]:
    page_number = 1
    no_more_listings = False
    no_listings_text = "There are currently no listings that match your search criteria"
    urls = []

    while True and not no_more_listings:
        try_count = 0
        while try_count < max_retries:
            print(f"Trying to scrape page {page_number} with try {try_count}")
            try:
                if page_number > 1:
                    state_url = f"{state_url}?page={page_number}"
                async with AsyncClient(proxy=get_proxy_settings()) as client:
                    await asyncio.sleep(1)
                    response = await client.get(state_url)
                    response.raise_for_status()

                    html = HTMLParser(response.text)

                    if no_listings_text in html.text():
                        print(f"No listings found on page {page_number}")
                        no_more_listings = True
                        break

                    script_tag = html.css_first('script[type="application/ld+json"]')

                    if script_tag and script_tag.text():
                        json_data = json.loads(script_tag.text())

                        # Extract URLs from itemListElement
                        if (
                            "mainEntity" in json_data
                            and "itemListElement" in json_data["mainEntity"]
                        ):
                            listings = json_data["mainEntity"]["itemListElement"]
                            print(
                                f"Found {len(listings)} listings on page {page_number}"
                            )
                            urls.extend(
                                [
                                    {
                                        "url": item["item"]["url"],
                                        "name": item["item"]["name"],
                                        "image": item["item"]["image"],
                                        "address": item["item"]["address"],
                                        "price": item["item"]["priceRange"],
                                        "telephone": item["item"]["telephone"],
                                    }
                                    for item in listings
                                    if "item" in item and "url" in item["item"]
                                ]
                            )
                            break
            except Exception as e:
                print(f"Error scraping page {page_number}: {e}")
                try_count += 1
                await asyncio.sleep(1)

        page_number += 1

    return urls


async def scrape_listing_page(page_url: str):
    async with AsyncClient(proxy=get_proxy_settings()) as client:
        proxy_check_response = await client.get("http://ip-api.com/json/?fields=61439")
        print(proxy_check_response.text, "proxy check response")
        response = await client.get(page_url)
        response.raise_for_status()

        html = HTMLParser(response.text)
        print(parse_ld_json(html), "parsed ld json")
        print(parse_html(html), "parsed html")


def parse_ld_json(html: HTMLParser):
    script_tag = html.css_first('script[type="application/ld+json"]')
    if script_tag and script_tag.text():
        json_data = json.loads(script_tag.text())
        return json_data
    return None


def parse_html(html: HTMLParser) -> dict:
    """
    Parse the HTML content of a business listing page

    Args:
        html (HTMLParser): The Selectolax HTML parser instance
    Returns:
        dict: The parsed business details
    """
    details = {}
    additional_info = {}

    # Get title
    title_element = html.css_first("h1")
    if title_element:
        details["title"] = title_element.text().strip()

    # Get location
    location_element = html.css_first("h2")
    if location_element:
        details["location"] = location_element.text().strip()

    # Get asking price
    price_element = html.css_first("#lblPrice")
    if price_element:
        details["asking_price"] = price_element.text().strip()

    # Get revenue
    revenue_element = html.css_first("#lblyrevenue")
    if revenue_element:
        details["annual_revenue"] = revenue_element.text().strip()

    # Get industry
    industry_element = html.css_first(".industry a")
    if industry_element:
        details["industry"] = industry_element.text().strip()

    # Get quick facts
    quick_facts = html.css(".quickFacts tr")
    for fact in quick_facts:
        label_element = fact.css_first(".label")
        value_element = fact.css_first("td:last-child span")

        if label_element and value_element:
            label = (
                label_element.text().strip().lower().replace(":", "").replace(" ", "_")
            )
            value = value_element.text().strip()

            if label not in details and label not in additional_info:
                if "year_established" in label:
                    details["business_age"] = value
                else:
                    additional_info[label] = value

    if "cash_flow" in additional_info and "ebitda" not in details:
        details["ebitda"] = additional_info["cash_flow"]
    if "ebitda" in details and "sde" not in details:
        details["sde"] = details["ebitda"]

    # Get detailed sections
    content = html.css_first(".busListingContent")
    if content:
        sections = content.text().split("\n")
        current_section = None
        section_content = []

        for line in sections:
            line = line.strip()
            if not line:
                continue

            if line.isupper():  # Assuming section headers are in uppercase
                if current_section and section_content:
                    section_key = (
                        current_section.lower().replace(":", "").replace(" ", "_")
                    )
                    section_text = " ".join(section_content)

                    if (
                        section_key not in details
                        and section_key not in additional_info
                    ):
                        if "business_overview" in section_key:
                            details["description"] = section_text
                        else:
                            additional_info[section_key] = section_text

                current_section = line
                section_content = []
            else:
                section_content.append(line)

    details["additional_info"] = additional_info
    return details