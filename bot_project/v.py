import requests
from datetime import datetime

# API-Football Credentials
API_KEY = "883a405b43c6f309dd7d091f6ec2b494"
API_URL = "https://v3.football.api-sports.io/fixtures"

def get_todays_competitions():
    today = datetime.today().strftime("%Y-%m-%d")  # Format: YYYY-MM-DD
    headers = {"x-apisports-key": API_KEY}
    params = {"date": today, "status": "NS"}  # NS = Not Started (Scheduled)

    response = requests.get(API_URL, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return set()

    data = response.json()
    if "response" not in data:
        print("Unexpected API response format.")
        return set()

    competitions = set()
    for fixture in data["response"]:
        league_name = fixture["league"]["name"]
        competitions.add(league_name)

    return competitions

def main():
    competitions = get_todays_competitions()
    if competitions:
        with open("list.txt", "w", encoding="utf-8") as f:
            for comp in sorted(competitions):
                f.write(comp + "\n")
        print("Competition list saved to list.txt")
    else:
        print("No competitions found for today.")

if __name__ == "__main__":
    main()
