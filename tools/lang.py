#!/usr/bin/env python3
"""Helps put a KUDU app into other languages.

    python tools/lang.py list  ../kududiff                 the texts the app shows, numbered (English)
    python tools/lang.py merge ../kududiff ml words.txt    makes src/<APP>/Lang/ml.txt from "number<TAB>text" lines
    python tools/lang.py check ../kududiff                 exit 1 when a language misses a text or fills in the wrong places

A language file (src/<APP>/Lang/<code>.txt) has a line for each text: the English, a tab, the same in that language.
{0}, {1}... stand for what the app fills in (a number, a name). The app looks texts up as they are shown
(shared/Core/Lang.cs), so the list here is found by reading the app's code: every piece of text in it that looks like
something a person reads.
"""
import os
import re
import sys

LANGS = ["ml", "hi", "es", "fr", "ar"]

SKIP_FILES = {"SelfTest.cs", "Screenshots.cs", "Lang.cs", "LangCommon.cs", "LangUi.cs", "Glyph.cs"}

# A single word right after one of these is a name the code uses, not something shown.
CODE_BEFORE = re.compile(
    r"(?:\b(?:Res|Styled|Icon|FindResource|TryFindResource|OpenSubKey|CreateSubKey|DeleteSubKey\w*|GetValue|SetValue|DeleteValue|"
    r"StartsWith|EndsWith|IndexOf|LastIndexOf|Equals|Replace|Split|Trim\w*|ToString|Parse\w*|TryParse\w*|GetEncoding|"
    r"Combine|Expect|Step|Wait|Note|GetManifestResourceStream|GetEnvironmentVariable|Has|Flag|Value|Option|"
    r"Regex|Match|IsMatch|Matches|DllImport|EntryPoint|GetMethod|GetProperty|GetField|nameof|Verb|Label|Button)\s*\(\s*(?:[\w.]+\s*,\s*)*"
    r"|\bcase\s+|[=!]=\s*|\bGroupName\s*=\s*|\bTag\s*=\s*|\bName\s*=\s*|\bVerb\s*=\s*|\bFileName\s*=\s*|\bArguments\s*=\s*|\[\s*)$")

SHOWN_BEFORE = re.compile(
    r"(?:\b(?:Text|Subtle|Heading|Button|Link|Chip|Tip|Label|Stat|Info|Error|Confirm|Ask|Dialog|Prepare|Banner|Section|Row|Option|Check|Radio)\s*\(\s*(?:[\w.]+\s*,\s*)*"
    r"|\b(?:Content|Header|Title|ToolTip|Text|Description)\s*=\s*|\?\s*|:\s*)$")


def literals(code):
    """Every text in C# code: (start, end, text with {n} where something is filled in, how many places)."""
    out = []
    i, n = 0, len(code)
    while i < n:
        c = code[i]
        if c == "/" and code.startswith("//", i):
            j = code.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and code.startswith("/*", i):
            j = code.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == "'":
            j = i + 1
            while j < n and code[j] != "'":
                j += 2 if code[j] == "\\" else 1
            i = j + 1
            continue
        m = re.match(r'(\$@|@\$|\$|@)?"', code[i:])
        if not m:
            i += 1
            continue
        prefix = m.group(1) or ""
        j = i + len(m.group(0))
        verbatim, interpolated = "@" in prefix, "$" in prefix
        text, holes = [], 0
        while j < n:
            ch = code[j]
            if verbatim and ch == '"':
                if code.startswith('""', j):
                    text.append('"')
                    j += 2
                    continue
                break
            if not verbatim and ch == '"':
                break
            if not verbatim and ch == "\\":
                e = code[j + 1]
                if e == "u":
                    text.append(chr(int(code[j + 2:j + 6], 16)))
                    j += 6
                    continue
                text.append({"n": "\n", "t": "\t", "r": "\r", "0": "\0"}.get(e, e))
                j += 2
                continue
            if interpolated and ch == "{":
                if code.startswith("{{", j):
                    text.append("{")
                    j += 2
                    continue
                depth, k = 1, j + 1
                while k < n and depth:
                    if code[k] == "{":
                        depth += 1
                    elif code[k] == "}":
                        depth -= 1
                    elif code[k] == '"':  # a text inside the filled-in part
                        k += 1
                        while k < n and code[k] != '"':
                            k += 2 if code[k] == "\\" else 1
                    k += 1
                text.append("{%d}" % holes)
                holes += 1
                j = k
                continue
            if interpolated and ch == "}" and code.startswith("}}", j):
                text.append("}")
                j += 2
                continue
            text.append(ch)
            j += 1
        out.append((i, j + 1, "".join(text), holes, interpolated))
        i = j + 1
    return out


def joined(code):
    """Texts as they'll be shown: pieces added together ("a " + x + " b") become one text with a place for x."""
    lits = literals(code)
    result = []
    k = 0
    while k < len(lits):
        start, end, text, holes, interpolated = lits[k]
        if not interpolated:
            text = re.sub(r"\{(\d)\}", r"{\1}", text)
            holes = len(set(re.findall(r"\{(\d)\}", text)))
        before = code[max(0, start - 160):start]
        # Something added in front: x + " files"
        lead = re.search(r"([\w.\)\]]+)\s*\+\s*$", before)
        if lead and not before.rstrip().endswith('"') and not re.search(r'"\s*\+\s*$', before):
            text = "{%d}" % holes + text
            holes += 1
            lead_hole = True
        else:
            lead_hole = False
        while True:
            after = code[end:end + 400]
            nxt = lits[k + 1] if k + 1 < len(lits) else None
            gap = code[end:nxt[0]] if nxt else None
            if nxt and re.fullmatch(r"\s*\+\s*", gap):
                # "a" + "b"
                add = nxt[2]
                if nxt[3]:
                    add = re.sub(r"\{(\d+)\}", lambda m: "{%d}" % (int(m.group(1)) + holes), add)
                text += add
                holes += nxt[3]
                end = nxt[1]
                k += 1
                continue
            if nxt and re.fullmatch(r"\s*\+\s*[^\"+;,]{1,120}?\s*\+\s*", gap) and gap.count("(") == gap.count(")"):
                add = nxt[2]
                text += "{%d}" % holes
                holes += 1
                if nxt[3]:
                    add = re.sub(r"\{(\d+)\}", lambda m: "{%d}" % (int(m.group(1)) + holes), add)
                text += add
                holes += nxt[3]
                end = nxt[1]
                k += 1
                continue
            if re.match(r"\s*\+\s*[\w(]", after) and not re.match(r'\s*\+\s*\$?@?"', after):
                text += "{%d}" % holes
                holes += 1
            break
        result.append((start, text, holes, before, lead_hole))
        k += 1
    return result


def looks_shown(text, before, theme_keys):
    t = text.strip()
    if len(t) < 2 or len(text) > 900:
        return False
    plain = re.sub(r"\{\d\}", "", t)
    letters = sum(ch.isalpha() and ord(ch) < 128 for ch in plain)
    if letters < 2:
        return False
    if any(ord(ch) > 0x2FF and ch not in "…•‘’“”–—→←↑↓✓✕×·♥›‹" for ch in plain):
        return False  # already another language (language names, sample text)
    lead = re.sub(r"^(\{\d\}\s*)+", "", t)
    if re.search(r"</?\w+[^>]*>|=>|\(\);|\\[bdws]|;\s*$|^https?:|^[A-Za-z]:\\|^--?\w|\bfunction\b|\bvar \w+ =|^\w+://", t) or re.match(r"\s*[{\[<]", lead):
        return False
    if re.fullmatch(r"[yMdHhmsftzg\-/:., ']+", t) or re.fullmatch(r"[#0,.%\- ]+", t):
        return False  # date and number formats
    if "|*." in t:
        return True
    words = plain.split()
    if len(words) >= 2:
        # A sentence or a label; but not code-like text (paths, switches, keys with dots or underscores throughout).
        if all(re.fullmatch(r"[\w.\-\\/:=*%@#<>()\[\]{}|&;,+\"']+", w) and re.search(r"[_\\/=<>{}|;@#]|\w\.\w", w) for w in words):
            return False
        return True
    w = words[0] if words else ""
    if w in theme_keys:
        return False
    if CODE_BEFORE.search(before) and not SHOWN_BEFORE.search(before):
        return False
    core = w.strip(".,:;!?…()\"'")
    # One word: shown when it starts with a capital and is otherwise plain ("Open", "Settings…"), and isn't a
    # CodeName or an ALLCAPS/short code.
    if re.search(r"\{\d\}", t) and re.fullmatch(r"[a-z]{3,}", core):
        return True  # "{0} changes"
    if re.fullmatch(r"[A-Z][a-z]{1,}(?:-[a-z]+)?", core):
        return True
    if SHOWN_BEFORE.search(before) and re.fullmatch(r"[A-Za-z][A-Za-z'’\-]+", core) and not re.search(r"[a-z][A-Z]", core):
        return True
    return False


def app_folder(repo):
    src = os.path.join(repo, "src")
    for name in sorted(os.listdir(src)):
        if os.path.isfile(os.path.join(src, name, name + ".csproj")):
            return os.path.join(src, name)
    sys.exit(repo + ": no src/<APP>/<APP>.csproj found")


def escape(s):
    return s.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")


def unescape(s):
    return re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t", "r": "\r"}.get(m.group(1), m.group(1)), s)


def collect(repo):
    """The app's texts in the order they're met, each once."""
    folder = app_folder(repo)
    theme_keys = set()
    for root, _, files in os.walk(folder):
        for f in files:
            if f.endswith(".xaml"):
                theme_keys.update(re.findall(r'x:Key="([^"]+)"', open(os.path.join(root, f), encoding="utf-8-sig").read()))
    seen, order = set(), []
    for root, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if d not in ("bin", "obj"))
        for f in sorted(files):
            if not f.endswith(".cs") or f in SKIP_FILES:
                continue
            path = os.path.join(root, f)
            code = open(path, encoding="utf-8-sig").read()
            for start, text, holes, before, _ in joined(code):
                pieces = [text]
                if "|*." in text:
                    pieces = text.split("|")[0::2]  # the names in a file dialog's list of kinds
                for piece in pieces:
                    if piece.strip() != piece and piece.strip():
                        piece = piece.strip() if not re.search(r"\{\d\}", piece) else piece
                    if piece in seen or not looks_shown(piece, before, theme_keys):
                        continue
                    seen.add(piece)
                    order.append((piece, os.path.relpath(path, folder)))
    return order


def holes_of(s):
    return sorted(set(re.findall(r"\{(\d)\}", s)))


def read_lang(path):
    pairs = {}
    if os.path.isfile(path):
        for line in open(path, encoding="utf-8").read().split("\n"):
            if not line or line[0] == "#" or "\t" not in line:
                continue
            a, b = line.split("\t", 1)
            pairs[unescape(a)] = unescape(b)
    return pairs


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, repo = sys.argv[1], sys.argv[2]
    texts = collect(repo)
    lang_dir = os.path.join(app_folder(repo), "Lang")
    if cmd == "list":
        only_new = len(sys.argv) > 3 and sys.argv[3] == "new"
        have = read_lang(os.path.join(lang_dir, LANGS[0] + ".txt")) if only_new else {}
        last = None
        for n, (text, where) in enumerate(texts, 1):
            if text in have:
                continue
            if where != last:
                print("# " + where)
                last = where
            print("%d\t%s" % (n, escape(text)))
    elif cmd == "merge":
        code, source = sys.argv[3], sys.argv[4]
        path = os.path.join(lang_dir, code + ".txt")
        pairs = read_lang(path)
        bad = 0
        for line in open(source, encoding="utf-8").read().split("\n"):
            if not line.strip() or line[0] == "#":
                continue
            m = re.match(r"(\d+)\t(.*)$", line)
            if not m or not (1 <= int(m.group(1)) <= len(texts)):
                print("not understood: " + line[:80])
                bad += 1
                continue
            english = texts[int(m.group(1)) - 1][0]
            other = unescape(m.group(2))
            if holes_of(english) != holes_of(other):
                print("%s: the filled-in places differ: %r -> %r" % (m.group(1), english, other))
                bad += 1
                continue
            pairs[english] = other
        os.makedirs(lang_dir, exist_ok=True)
        known = [t for t, _ in texts if t in pairs]
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            for english in known:
                f.write(escape(english) + "\t" + escape(pairs[english]) + "\n")
        print("%s: %d of %d texts%s" % (path, len(known), len(texts), ", %d lines refused" % bad if bad else ""))
        sys.exit(1 if bad else 0)
    elif cmd == "check":
        failed = False
        for code in LANGS:
            pairs = read_lang(os.path.join(lang_dir, code + ".txt"))
            missing = [t for t, _ in texts if t not in pairs]
            wrong = [t for t, _ in texts if t in pairs and holes_of(t) != holes_of(pairs[t])]
            if missing or wrong:
                failed = True
                print("%s: %d missing, %d with other filled-in places" % (code, len(missing), len(wrong)))
                for t in (missing + wrong)[:15]:
                    print("    " + escape(t)[:110])
        print("%d texts, %s" % (len(texts), "not complete" if failed else "every language complete"))
        sys.exit(1 if failed else 0)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
