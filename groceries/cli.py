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

    # 3. Fuzzy match — each name is matched individually
    matched = set()
    for name in args.names:
        for recipe_name, _score in fuzzy_match(name, recipe_names):
            matched.add(recipe_name)
    matches = sorted(matched)

    if not matches:
        print(f"No recipes matching: {' '.join(args.names)}")
        return

    print(f"\nMatching recipes (adding to '{shopping_list}'):")
    for i, name in enumerate(matches, 1):
        print(f"  {i}. {name}")

    response = input("\nAdd to shopping list? [Y/n] ").strip().lower()
    if response and response not in ("y", "yes"):
        print("Cancelled.")
        return

    # 4. Append directly
    subprocess.run(
        [sys.executable, str(PROJECT_DIR / "ourgroceries_tool.py"),
         "append-recipes", shopping_list, json.dumps(matches, ensure_ascii=False)],
        cwd=PROJECT_DIR,
    )


def fuzzy_match(query, names):
    q = query.lower().strip()
    scored = []
    for name in names:
        n = name.lower()
        score = 0

        # remove emoji for matching
        n_clean = n.split(" ")[0] if " " in n else n
        # clean parentheses content for matching
        n_words = re.sub(r"[()]", "", n).split()

        if q == n:
            score = 100
        elif q in n:
            score = 90 if n.startswith(q) else 85
        else:
            q_words = [w for w in q.split() if len(w) >= 3]
            if q_words:
                hits = 0
                for qw in q_words:
                    if any(qw in nw for nw in n_words):
                        hits += 1
                score = (hits / len(q_words)) * 70

        if score >= 70:
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
        COMPREPLY=( $(compgen -W "add-recipe add-to-shopping-list categories list install" -- "$cur") )
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
    elif args.command == "install":
        cmd_install()


if __name__ == "__main__":
    main()
