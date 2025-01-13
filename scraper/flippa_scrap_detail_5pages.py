import asyncio
import json
from scraper.flippa_scrap_links_5page import scrape_detail_page  # Import scrape_detail_page function
import os

async def scrape_all_details():
    """
    Read links from file and scrape details for each link.
    """
    # Step 1: Read links from the saved file
    try:
        with open("scraped_links/flippa_links.txt", "r") as file:
            links = [line.strip() for line in file.readlines()]
    except FileNotFoundError:
        print("Error: flippa_links.txt not found. Run scrape_links.py first.")
        return

    # Step 2: Scrape details for each link
    all_details = []
    for idx, link in enumerate(links, start=1):
        print(f"\nScraping details for link {idx}/{len(links)}: {link}")
        details = await scrape_detail_page(link)
        if details:  # Only add valid scraped data
            all_details.append(details)

        # Optional delay between requests
        await asyncio.sleep(3)

    output_dir = "scraped_detail_page"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "flippa_details.json")
    # Step 3: Save details to a JSON file
    with open(output_file, "w") as file:
        json.dump(all_details, file, indent=4)
    print(f"\nDetails saved to {output_file}")

if __name__ == "__main__":
    asyncio.run(scrape_all_details())
