import requests

url = "https://jsearch.p.rapidapi.com/search"

# MUST use params, not json or data
querystring = {"query": "Software Engineer"}

headers = {
    "X-RapidAPI-Key": "34ffed990amsh67a072a10b79350p1a89dcjsnb1f189669168",
    "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
}

# MUST be requests.get()
response = requests.get(url, headers=headers, params=querystring)
print(response.json())