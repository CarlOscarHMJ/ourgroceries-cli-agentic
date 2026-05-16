import argparse
import os
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
    names = " ".join(args.names)
    prompt = (
        "Follow the 'Add to shopping list' section in AGENTS.md "
        "to add these to our shopping list. "
        "The user has already confirmed — do NOT ask for confirmation, "
        "just add them:\n\n"
        f"{names}"
    )
    run_opencode(prompt)


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
