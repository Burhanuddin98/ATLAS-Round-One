from material_db import MaterialDB    # <-- direct import


if __name__ == "__main__":
    db = MaterialDB.from_json("material_library_1_3oct.json")
    print("Bands (Hz):", db.native_bands[:10], "…")
    print("Materials loaded:", len(db.items))
    for name, mat in list(db.items.items())[:5]:
        print(f"{name}: α[500Hz]={mat.alpha[db.native_bands.tolist().index(500)]}")
