import json

with open(r"e:\git_fork_folder\global_commodity_traffic\temp_api_test.json") as f:
    data = json.load(f)

records = data.get("data", [])
if records:
    print("All fields in first record:")
    for k, v in records[0].items():
        print(f"  {k}: {v}")
