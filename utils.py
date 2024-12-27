# utils.py
import httpx

async def log_ip_address(client):
    """
    Log the public IP address by sending a request to httpbin.org/ip
    """
    try:
        response = await client.get("https://httpbin.org/ip")
        ip_address = response.json().get("origin")
        print(f"Request made from IP: {ip_address}")
    except httpx.RequestError as e:
        print(f"Failed to log IP: {e}")
