from pprint import pprint
import requests

r = requests.get('https://api.github.com/repos/oatsu-gh/EnuPitch/releases')


pprint(r.json())
for item in r.json():
    print("tag_name: ", item["tag_name"])
    print("name: ", item["name"])
    print("download count: ", item["assets"][0]["download_count"])
    print("")
