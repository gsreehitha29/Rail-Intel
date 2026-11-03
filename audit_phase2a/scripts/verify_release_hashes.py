import hashlib
import json
import pathlib
import sys
import zipfile

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha256_file(filepath: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    root = pathlib.Path(".")
    release_dir = root / "03_graph_construction" / "release"
    pkg_dir = release_dir / "rail-intel-v2.0-open"
    lock_file = release_dir / "rail-intel-v2.0-open.LOCK.md"
    zip_file = release_dir / "rail-intel-v2.0-open.zip"
    manifest_file = pkg_dir / "manifest.json"
    sums_file = pkg_dir / "SHA256SUMS"

    results = {
        "status": "PASS",
        "release_identity": "rail-intel-v2.0-open",
        "zip_archive": {
            "path": str(zip_file),
            "size_bytes": zip_file.stat().st_size if zip_file.exists() else None,
            "expected_sha256": "b1e3908167abb2aa91238046e9b25ac50a88ba3645077cb028b45331c449eeda",
            "computed_sha256": sha256_file(zip_file) if zip_file.exists() else None,
            "matches": False,
            "entries_verified": {}
        },
        "disk_files": {},
        "notes": []
    }

    # 1. Verify ZIP archive
    if zip_file.exists():
        computed_zip = results["zip_archive"]["computed_sha256"]
        if computed_zip == results["zip_archive"]["expected_sha256"]:
            results["zip_archive"]["matches"] = True
            print(f"[OK] ZIP archive hash matches canonical lock: {computed_zip}")
        else:
            results["status"] = "FAIL"
            print(f"[FAIL] ZIP archive hash mismatch: {computed_zip}")

    # 2. Parse manifest.json
    manifest_sums = {}
    if manifest_file.exists():
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
            for item in manifest_data.get("files", []):
                manifest_sums[item["path"]] = {
                    "expected_sha256": item["sha256"],
                    "expected_bytes": item.get("bytes"),
                    "rows": item.get("rows")
                }

    # 3. Verify ZIP internal members
    with zipfile.ZipFile(zip_file) as z:
        for name in z.namelist():
            # e.g. rail-intel-v2.0-open/graph/edges.csv
            rel = name.split("/", 1)[1] if "/" in name else name
            if not rel:
                continue
            data = z.read(name)
            h = sha256_bytes(data)
            exp = manifest_sums.get(rel, {}).get("expected_sha256")
            matches = (h == exp) if exp else True
            results["zip_archive"]["entries_verified"][rel] = {
                "bytes": len(data),
                "sha256": h,
                "matches_manifest": matches
            }
            if not matches and exp:
                results["status"] = "FAIL"
                print(f"[FAIL] Zip member {rel} mismatch against manifest: {h} vs {exp}")
            else:
                print(f"[OK] Zip member {rel} verified ({h[:16]}...)")

    # 4. Check disk directory
    for rel_path, exp_info in manifest_sums.items():
        disk_path = pkg_dir / rel_path
        if not disk_path.exists():
            results["disk_files"][rel_path] = {"error": "missing"}
            results["status"] = "FAIL"
            continue
        raw_bytes = disk_path.read_bytes()
        disk_hash = sha256_bytes(raw_bytes)
        lf_hash = sha256_bytes(raw_bytes.replace(b"\r\n", b"\n"))
        exp_hash = exp_info["expected_sha256"]

        is_exact = (disk_hash == exp_hash)
        is_lf_match = (lf_hash == exp_hash)

        results["disk_files"][rel_path] = {
            "size_disk": len(raw_bytes),
            "sha256_disk": disk_hash,
            "expected_sha256": exp_hash,
            "exact_match": is_exact,
            "crlf_normalized_match": is_lf_match
        }

        if is_exact:
            print(f"[OK] Disk file {rel_path} exact byte match")
        elif is_lf_match:
            print(f"[NOTE] Disk file {rel_path} matches after CRLF->LF normalization (Windows git checkout artifact)")
            results["notes"].append(f"{rel_path}: CRLF line ending difference on Windows checkout")
        else:
            results["status"] = "FAIL"
            print(f"[FAIL] Disk file {rel_path} differs even after line ending normalization!")

    out_file = root / "audit_phase2a" / "results" / "hash_verification.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nVerification summary saved to {out_file}")
    print(f"Overall status: {results['status']}")

if __name__ == "__main__":
    main()
