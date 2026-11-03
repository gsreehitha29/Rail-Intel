import pathlib

def main():
    root = pathlib.Path(__file__).resolve().parents[2]
    work_dir = root / "03_graph_construction" / "graph_v2_0_open" / "work"
    for p in sorted(work_dir.glob("*")):
        if p.is_file():
            print(f"{p.name} ({p.stat().st_size} bytes)")

if __name__ == "__main__":
    main()
