# OurGroceries Recipe Creation Tool

Turn recipe text into structured shopping lists in [OurGroceries](https://www.ourgroceries.com)
using an AI agent. Paste a recipe from any website, a screenshot, or just type
the ingredients — the agent parses it, categorizes every ingredient, and adds
it as a recipe list. Later, with one command, append all items from any recipe
to your main shopping list.

The agent handles the tedious parts automatically:

- **Categorization** — matches each ingredient to the right OurGroceries category (Dairy, Bread, Produce, etc.)
- **Language** — all content in your configured language (Danish by default)
- **Scaling** — recipes are scaled to 3 adults by default, with portion counts in the notes
- **Shopping list sync** — fuzzy-match recipe names to append items to your main shopping list

## Prerequisites

- **Python 3.11+**
- **[opencode](https://opencode.ai/download)** — the AI agent
- A **OurGroceries** account

## Install

```bash
cd ourGroceriesShooping
pip install -e .
groceries install
```

`groceries install` sets up tab completion and checks that opencode is available.

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```
OURGROCERIES_USERNAME=you@email.com
OURGROCERIES_PASSWORD=your-password
LANGUAGE=Danish
```

The `LANGUAGE` setting controls what language recipe names, notes, and
ingredients are written in (see `AGENTS.md`).

## Usage

```bash
# Add a recipe — text, URL, file, or stdin
groceries add-recipe "Pancakes: 3 eggs, 2 dl milk, 150 g flour, butter"
groceries add-recipe https://example.com/recipe
cat recipe.txt | groceries add-recipe

# Add items from recipes to your shopping list
groceries add-to-shopping-list cauliflower tacos pancakes

# List all recipes and categories
groceries list
groceries categories
```

### Direct tool usage (without the agent)

```bash
python3 ourgroceries_tool.py categories
python3 ourgroceries_tool.py list-recipes
python3 ourgroceries_tool.py add-recipe recipe.json
python3 ourgroceries_tool.py append-recipes "Shopping List" '["Recipe Name"]'
```

## How it works

```
groceries add-recipe "Pancakes: 3 eggs, 2 dl milk…"
       │
       ▼  subprocess
opencode run "Add this recipe…"
       │
       ▼  reads AGENTS.md
agent: 1. Parses recipe → name + ingredients
       2. Runs ourgroceries_tool.py categories → gets category IDs
       3. Matches each ingredient to a category
       4. Writes recipe.json, runs add-recipe, cleans up
```

The agent follows `AGENTS.md` for naming rules, quantity formatting,
spelling fixes, plural forms, and scaling to 3 adults.

## License

MIT — see [LICENSE](LICENSE)
