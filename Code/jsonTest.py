import json

with open('config.json', 'r') as file:
    config = json.load(file)
roi = int(config["array"].split(',')[0])
for s in config["array"].split(','):
    print(int(s))
# print(roi)