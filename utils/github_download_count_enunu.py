import requests

r = requests.get('https://api.github.com/repos/oatsu-gh/ENUNU/releases', timeout=10)

for item in r.json():
    print('tag_name: ', item['tag_name'])
    print('name: ', item['name'])
    print(item['assets'][0]['url'])
    print('download count: ', item['assets'][0]['download_count'])
    print('')

input()
