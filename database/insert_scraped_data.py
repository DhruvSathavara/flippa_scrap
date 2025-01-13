import json
from supabase_client import supabase  # Import Supabase client

def insert_data_to_supabase(data):
    """
    Insert a single record into the Supabase database.
    """
    response = supabase.table("flippa_scraped_listings").insert(data).execute()

    # Check if the response contains inserted data
    if response.data:
        print(f"Inserted successfully: {response.data}")
    else:
        print(f"Failed to insert: {data['source_url']} - Response: {response}")



def process_scraped_data(file_path):
    """
    Read data from a JSON file and insert it into Supabase.
    """
    with open(file_path, "r") as file:
        listings = json.load(file)
        for listing in listings:
            # Transform data into the required schema
            data = {
                "source_url": listing.get("source_url"),
                "title": listing.get("title"),
                "industry": listing.get("industry"),
                "description": listing.get("description"),
                "asking_price": listing.get("asking_price"),
                "about_business": listing.get("additional_info", {}).get("about_business"),
            }
            insert_data_to_supabase(data)


if __name__ == "__main__":
    # File path of your scraped detail page JSON
    json_file_path = "scraped_detail_page/flippa_details.json"
    process_scraped_data(json_file_path)
