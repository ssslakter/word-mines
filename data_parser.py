words = []

with open("data.txt", encoding="utf-8") as f:
    for line in f:
        words.append(f'{line.replace("\n", "")}')

with open("parsed_data.txt", "w", encoding="utf-8") as f:
    f.write('\",\"'.join(words))