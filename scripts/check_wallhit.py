import sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
try:
    with open('matching_v3/research_results/wallhit_commercial_quality_20260630.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"Rounds completed: {len(data)}")
    for r in data:
        print(f"Round {r['round']}: {r['role']} - {len(r['answer'])} chars")
        print(r['answer'][:500])
        print("---")
except FileNotFoundError:
    print("File not found - script may not have completed")
except Exception as e:
    print(f"Error: {e}")
