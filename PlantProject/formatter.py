def format_results(results):
    """
    Formats prediction results into a clean professional structure.
    """

    formatted_output = []

    for rank, plant in enumerate(results, start=1):
        formatted_output.append({
            "Rank": rank,
            "Common Name": plant.get("Common_Name", ""),
            "Scientific Name": plant.get("Scientific_Name", ""),
            "Family": plant.get("Family", ""),
            "Plant Type": plant.get("Plant_Type", ""),
            "Habitat": plant.get("Habitat", ""),
            "Leaf Shape": plant.get("Leaf_Shape", ""),
            "Flower Color": plant.get("Flower_Color", ""),
            "Medicinal Uses": plant.get("Medicinal_Uses", ""),
            "Culinary Uses": plant.get("Culinary_Uses", ""),
            "Industrial Uses": plant.get("Industrial_Uses", ""),
            "Match %": plant.get("Match_Percentage", 0)
        })

    return formatted_output


def print_results(results):
    """
    Prints results in clean console format.
    """

    print("\n🌿 BEST MATCHING PLANTS\n")

    for plant in results:
        print(f"Rank: {plant['Rank']}")
        print(f"Match Confidence: {plant['Match %']} %")
        print(f"Common Name: {plant['Common Name']}")
        print(f"Scientific Name: {plant['Scientific Name']}")
        print(f"Family: {plant['Family']}")
        print(f"Plant Type: {plant['Plant Type']}")
        print(f"Habitat: {plant['Habitat']}")
        print(f"Leaf Shape: {plant['Leaf Shape']}")
        print(f"Flower Color: {plant['Flower Color']}")
        print(f"Medicinal Uses: {plant['Medicinal Uses']}")
        print(f"Culinary Uses: {plant['Culinary Uses']}")
        print(f"Industrial Uses: {plant['Industrial Uses']}")
        print("-" * 50)
