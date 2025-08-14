import requests, json

url = "https://www.dropbox.com/scl/fi/oiggh3m4d9qbtxyw8iqxm/version.json?rlkey=yt8908hx3vk1bkehtksipn4n6&st=93mf3osg&dl=1"
resp = requests.get(url)
print(json.loads(resp.text))
