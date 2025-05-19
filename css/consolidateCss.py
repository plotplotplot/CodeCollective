import os

ignoreList = ['calendar.css', 'master.css']
content = ''
for file in os.listdir('.'):
    if file in ignoreList:
        print(f"Skipping {file}")
        continue
    if file.endswith('.css'):
        with open(file, 'r') as f:
            content += f.read()
        print(f"Consolidated {file} into master.css")

with open('master.css', 'w+') as f:
    f.write(content)