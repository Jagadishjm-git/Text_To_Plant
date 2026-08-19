# Auto-fix CSV to ensure only 3 columns

input_file = "plants.csv"
output_file = "plants_clean.csv"

with open(input_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

cleaned_lines = []

for line in lines:
    parts = line.strip().split(",")

    # keep first 2 columns, merge rest into description
    if len(parts) > 3:
        new_line = parts[0] + "," + parts[1] + "," + " ".join(parts[2:])
    else:
        new_line = line.strip()

    cleaned_lines.append(new_line)

with open(output_file, "w", encoding="utf-8") as f:
    f.write("\n".join(cleaned_lines))

print("SUCCESS: plants_clean.csv created successfully")
