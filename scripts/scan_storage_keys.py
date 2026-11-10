import os

matches = []
for root, dirs, files in os.walk(r"frontend\src"):
    for f in files:
        if f.endswith((".ts", ".tsx")):
            fp = os.path.join(root, f)
            with open(fp, "r", encoding="utf-8") as file:
                text = file.read()
                if "localStorage" in text:
                    for line in text.splitlines():
                        if "localStorage" in line:
                            matches.append(f"{fp}: {line.strip()[:100]}")

for m in matches:
    print(m)
