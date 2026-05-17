import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import argcomplete
except ImportError:
    argcomplete = None

PROJECT_DIR = Path(__file__).resolve().parent.parent


def run_opencode(message: str):
    subprocess.run(
        ["opencode", "run", "--model", "opencode/big-pickle", message],
        cwd=PROJECT_DIR,
        stdin=subprocess.DEVNULL,
    )


def cmd_add_recipe(args):
    content = ""

    # Priority: piped data first, then URL/file/text arg
    if not sys.stdin.isatty():
        content = sys.stdin.read().strip()

    if not content:
        source = args.input
        if source.startswith(("http://", "https://")):
            content = source
        elif source != "-" and os.path.isfile(source):
            with open(source) as f:
                content = f.read().strip()
        elif source != "-":
            content = source

    if not content:
        print("Error: no input provided", file=sys.stderr)
        sys.exit(1)

    prompt = (
        "Add this recipe to OurGroceries following the rules in AGENTS.md:\n\n"
        f"{content}"
    )
    run_opencode(prompt)


def cmd_add_to_shopping_list(args):
    # 1. Get all recipe names
    result = subprocess.run(
        [sys.executable, str(PROJECT_DIR / "ourgroceries_tool.py"), "list-recipes"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    recipe_names = [n for n in result.stdout.strip().split("\n") if n]

    # 2. Get shopping list name
    result = subprocess.run(
        [sys.executable, str(PROJECT_DIR / "ourgroceries_tool.py"),
         "list-shopping-lists"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    shopping_lists = [n for n in result.stdout.strip().split("\n") if n]
    if not shopping_lists:
        print("Error: no shopping lists found", file=sys.stderr)
        sys.exit(1)
    shopping_list = shopping_lists[0]

    # 3. Split args by comma, then match + confirm each query
    queries = []
    for arg in args.names:
        for piece in arg.split(","):
            piece = piece.strip()
            if piece:
                queries.append(piece)

    for query in queries:
        matched = set()
        for recipe_name, _score in fuzzy_match(query, recipe_names):
            matched.add(recipe_name)
        matches = sorted(matched)

        if not matches:
            print(f"\nNo recipes matching '{query}'")
            continue

        print(f"\nMatching '{query}':")
        for i, name in enumerate(matches, 1):
            print(f"  {i}. {name}")

        response = input(
            "Add which? [Y=all / n=none / 1,3 / 1-3] "
        ).strip().lower()

        if response in ("n", "no"):
            continue

        selected = set()
        if response in ("", "y", "yes", "a", "all"):
            selected = set(matches)
        else:
            import re as _re
            tokens = _re.split(r"[,\s]+", response)
            for token in tokens:
                token = token.strip()
                if not token:
                    continue
                if "-" in token:
                    try:
                        start, end = token.split("-", 1)
                        for n in range(int(start), int(end) + 1):
                            if 1 <= n <= len(matches):
                                selected.add(matches[n - 1])
                    except ValueError:
                        print(f"Ignoring invalid range: {token}", file=sys.stderr)
                else:
                    try:
                        n = int(token)
                        if 1 <= n <= len(matches):
                            selected.add(matches[n - 1])
                    except ValueError:
                        print(f"Ignoring invalid input: {token}", file=sys.stderr)

        if not selected:
            continue

        subprocess.run(
            [sys.executable, str(PROJECT_DIR / "ourgroceries_tool.py"),
             "append-recipes", shopping_list,
             json.dumps(sorted(selected), ensure_ascii=False)],
            cwd=PROJECT_DIR,
        )


def levenshtein(s1, s2):
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    if len(s2) == 0:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            curr.append(min(
                prev[j + 1] + 1,
                curr[j] + 1,
                prev[j] + (c1 != c2),
            ))
        prev = curr
    return prev[-1]


def fuzzy_match(query, names):
    q = query.lower().strip()
    scored = []
    for name in names:
        n = name.lower()
        score = 0

        n_words = re.sub(r"[()]", "", n).split()

        if q == n:
            score = 100
        elif q in n:
            score = 90 if n.startswith(q) else 85
        else:
            q_clean = re.sub(r"[()]", "", q)
            q_words = [w for w in q_clean.split() if len(w) >= 3]
            if q_words:
                hits = 0
                for qw in q_words:
                    if any(qw in nw for nw in n_words):
                        hits += 1
                    else:
                        for nw in n_words:
                            d = levenshtein(qw, nw)
                            maxlen = max(len(qw), len(nw))
                            if maxlen > 0 and (d / maxlen) <= 0.4:
                                hits += 0.7
                                break
                score = (hits / len(q_words)) * 70

        if score >= 55:
            scored.append((name, score))

    scored.sort(key=lambda x: -x[1])
    return scored


def cmd_list_recipes():
    subprocess.run(
        [sys.executable, str(PROJECT_DIR / "ourgroceries_tool.py"), "list-recipes"],
        cwd=PROJECT_DIR,
    )


def cmd_categories():
    subprocess.run(
        [sys.executable, str(PROJECT_DIR / "ourgroceries_tool.py"), "categories"],
        cwd=PROJECT_DIR,
    )


def cmd_clear_list():
    result = subprocess.run(
        [sys.executable, str(PROJECT_DIR / "ourgroceries_tool.py"),
         "list-shopping-lists"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    shopping_lists = [n for n in result.stdout.strip().split("\n") if n]
    if not shopping_lists:
        print("Error: no shopping lists found", file=sys.stderr)
        sys.exit(1)
    shopping_list = shopping_lists[0]

    resp = input(f"Remove ALL items from '{shopping_list}'? [y/N] ").strip().lower()
    if resp not in ("y", "yes"):
        print("Cancelled.")
        return

    subprocess.run(
        [sys.executable, str(PROJECT_DIR / "ourgroceries_tool.py"),
         "clear-list", shopping_list],
        cwd=PROJECT_DIR,
    )


def cmd_install():
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", str(PROJECT_DIR)],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)

    # Check for opencode
    if not shutil.which("opencode"):
        print("WARNING: opencode not found on PATH.", file=sys.stderr)
        print("Install it from https://opencode.ai/download", file=sys.stderr)
        print()

    # Add self-contained tab completion to ~/.bashrc
    bashrc = Path.home() / ".bashrc"
    marker = "# groceries tab completion start"
    completion_block = f'''{marker}
_groceries() {{
    local cur="${{COMP_WORDS[COMP_CWORD]}}"
    local prev="${{COMP_WORDS[COMP_CWORD-1]}}"
    if [[ ${{COMP_CWORD}} -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "add-recipe add-to-shopping-list categories list clear install" -- "$cur") )
    fi
}}
complete -F _groceries groceries
# groceries tab completion end'''

    if bashrc.exists():
        content = bashrc.read_text()
        if marker in content:
            # Replace existing block
            import re
            content = re.sub(
                r'# groceries tab completion start.*?# groceries tab completion end\n?',
                '',
                content,
                flags=re.DOTALL,
            )
            print("Updated tab completion in ~/.bashrc")
        else:
            print("Added tab completion to ~/.bashrc")
        # Clean up any leftover old-style completion lines
        for old in [
            'eval "$(register-python-argcomplete groceries)"\n',
            '# Tab completion for groceries\n',
            'eval "$(register-python-argcomplete groceries)"',
            '# Tab completion for groceries',
        ]:
            content = content.replace(old, '')
        bashrc.write_text(content.rstrip() + '\n\n' + completion_block + '\n')
    else:
        bashrc.write_text(f'# ~/.bashrc\n\n{completion_block}\n')
        print("Created ~/.bashrc with tab completion")

    print("Run 'exec bash' or open a new terminal to activate.")

    print("Installed! Use 'groceries' from anywhere:")
    print()
    print("  groceries add-recipe <text | url | file>")
    print("  groceries add-to-shopping-list <recipe names...>")
    print("  groceries list")
    print("  groceries categories")
    print("  groceries clear")


def main():
    parser = argparse.ArgumentParser(
        description="OurGroceries recipe and shopping list tool"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add-recipe", help="Add a recipe to OurGroceries")
    p_add.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Recipe text, URL, file path, or stdin (default)",
    )

    p_shop = sub.add_parser(
        "add-to-shopping-list", help="Add items from recipes to shopping list"
    )
    p_shop.add_argument("names", nargs="+", help="Recipe name(s) to add")

    sub.add_parser("categories", help="List available categories")
    sub.add_parser("list", help="List all recipes")
    sub.add_parser("clear", help="Remove all items from shopping list")
    sub.add_parser("install", help="Install the groceries command globally")

    if argcomplete:
        argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if args.command == "add-recipe":
        cmd_add_recipe(args)
    elif args.command == "add-to-shopping-list":
        cmd_add_to_shopping_list(args)
    elif args.command == "categories":
        cmd_categories()
    elif args.command == "list":
        cmd_list_recipes()
    elif args.command == "clear":
        cmd_clear_list()
    elif args.command == "install":
        cmd_install()


if __name__ == "__main__":
    main()
