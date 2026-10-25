#!/usr/bin/env python3
"""Copies the shared KUDU code into the apps, or checks that an app's copy matches.

    python sync.py ../kudutree ../kudusync ...     copy shared/ into each app
    python sync.py --check ../kudutree             exit 1 if the app's copy differs

Each file in shared/ goes to the same place under the app's src/<APP>/ folder, with the KuduApp namespace changed
to the app's own (its RootNamespace) and a header saying where it comes from. The app's .kudu-common file records
which kudu-common commit it has and which files came from here, so files no longer shared are removed next time.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SHARED = os.path.join(HERE, "shared")
RECORD = ".kudu-common"
HEADER = (
    "// Shared KUDU code: this file comes from kudu-common (https://github.com/azeembukhariprivate/kudu-common).\n"
    "// Change it there and run its sync script; the build fails when this copy differs from kudu-common.\n"
)


def app_folder(repo):
    """The app's project folder (src/<APP>) and its root namespace."""
    src = os.path.join(repo, "src")
    for name in sorted(os.listdir(src)) if os.path.isdir(src) else []:
        project = os.path.join(src, name, name + ".csproj")
        if os.path.isfile(project):
            text = open(project, encoding="utf-8-sig").read()
            m = re.search(r"<RootNamespace>\s*([\w.]+)\s*</RootNamespace>", text)
            return os.path.join(src, name), (m.group(1) if m else name)
    sys.exit(f"{repo}: no src/<APP>/<APP>.csproj found")


def shared_files():
    for root, _, files in os.walk(SHARED):
        for f in sorted(files):
            if f.endswith((".cs", ".xaml")):
                yield os.path.relpath(os.path.join(root, f), SHARED).replace(os.sep, "/")


def render(rel, namespace):
    text = open(os.path.join(SHARED, rel), encoding="utf-8").read()
    return HEADER + re.sub(r"\bKuduApp\b", namespace, text)


def commit():
    try:
        sha = subprocess.check_output(["git", "-C", HERE, "rev-parse", "HEAD"], text=True).strip()
        dirty = subprocess.check_output(["git", "-C", HERE, "status", "--porcelain", "shared"], text=True).strip()
        return sha + ("-modified" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def recorded(repo):
    path = os.path.join(repo, RECORD)
    if not os.path.isfile(path):
        return None, []
    lines = open(path, encoding="utf-8").read().splitlines()
    sha = next((l.split(" ", 1)[1] for l in lines if l.startswith("commit ")), None)
    files = [l[2:] for l in lines if l.startswith("- ")]
    return sha, files


def sync(repo):
    folder, namespace = app_folder(repo)
    files = list(shared_files())
    changed = 0
    for rel in files:
        target = os.path.join(folder, rel)
        text = render(rel, namespace)
        old = open(target, encoding="utf-8").read() if os.path.isfile(target) else None
        if old != text:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            changed += 1
    _, before = recorded(repo)
    for rel in before:
        if rel not in files and os.path.isfile(os.path.join(folder, rel)):
            os.remove(os.path.join(folder, rel))  # no longer shared
            changed += 1
    with open(os.path.join(repo, RECORD), "w", encoding="utf-8", newline="\n") as f:
        f.write("# Shared code copied from https://github.com/azeembukhariprivate/kudu-common by its sync.py.\n")
        f.write(f"commit {commit()}\n")
        f.write(f"folder {os.path.relpath(folder, repo).replace(os.sep, '/')}\n")
        f.writelines(f"- {rel}\n" for rel in files)
    print(f"{repo}: {changed} file(s) updated ({namespace})")


def check(repo):
    folder, namespace = app_folder(repo)
    problems = []
    for rel in shared_files():
        target = os.path.join(folder, rel)
        if not os.path.isfile(target):
            problems.append(f"missing: {rel}")
        elif open(target, encoding="utf-8").read().replace("\r\n", "\n") != render(rel, namespace):
            problems.append(f"differs: {rel}")
    for p in problems:
        print(f"{repo}: {p}")
    if problems:
        print(f"{repo}: the shared code differs from kudu-common. Make the change in kudu-common and run its sync.py.")
        return False
    print(f"{repo}: shared code matches kudu-common")
    return True


def main(args):
    if not args:
        sys.exit(__doc__)
    if args[0] == "--check":
        ok = all([check(repo) for repo in args[1:]])
        sys.exit(0 if ok else 1)
    for repo in args:
        sync(repo)


if __name__ == "__main__":
    main(sys.argv[1:])
