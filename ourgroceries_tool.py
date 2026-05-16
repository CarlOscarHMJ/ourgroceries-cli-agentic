import asyncio, json, os, sys
from dotenv import load_dotenv
from ourgroceries import OurGroceries

load_dotenv()

USERNAME = os.environ.get("OURGROCERIES_USERNAME") or ""
PASSWORD = os.environ.get("OURGROCERIES_PASSWORD") or ""

async def categories():
    og = OurGroceries(USERNAME, PASSWORD)
    await og.login()
    data = await og.get_category_items()
    for cat in data["list"]["items"]:
        print(f"{cat['value']}|{cat['id']}")

async def add_recipe(recipe):
    og = OurGroceries(USERNAME, PASSWORD)
    await og.login()

    cat_data = await og.get_category_items()
    cat_map = {c["value"]: c["id"] for c in cat_data["list"]["items"]}

    name = recipe["name"]

    overview = await og.get_my_lists()
    for kind in ("shoppingLists", "recipes"):
        for lst in overview.get(kind, []):
            if lst["name"] == name:
                await og.delete_list(lst["id"])

    await og.create_list(name, list_type="RECIPE")
    overview = await og.get_my_lists()
    list_id = None
    for kind in ("recipes", "shoppingLists"):
        for lst in overview.get(kind, []):
            if lst["name"] == name:
                list_id = lst["id"]
                break
        if list_id:
            break

    items = []

    recipe_note = recipe.get("note")
    if recipe_note:
        items.append(("📝 " + recipe_note, None, None))

    for ing in recipe.get("ingredients", []):
        cat_id = None
        if isinstance(ing, dict):
            item_name = ing.get("name", "")
            cat_name = ing.get("category", "")
            note = ing.get("note")
            cat_id = cat_map.get(cat_name) if cat_name else None
        else:
            item_name = ing
            note = None
        items.append((item_name, cat_id, note))

    if items:
        await og.add_items_to_list(list_id, items)

    print(f"Created list '{name}' with {len(items)} items (id: {list_id})")

async def list_recipes():
    og = OurGroceries(USERNAME, PASSWORD)
    await og.login()
    overview = await og.get_my_lists()
    for r in overview.get("recipes", []):
        print(r["name"])


async def list_shopping_lists():
    og = OurGroceries(USERNAME, PASSWORD)
    await og.login()
    overview = await og.get_my_lists()
    for sl in overview.get("shoppingLists", []):
        print(sl["name"])


async def append_recipes(shopping_list_name, recipe_names):
    og = OurGroceries(USERNAME, PASSWORD)
    await og.login()

    overview = await og.get_my_lists()

    list_id = None
    for sl in overview.get("shoppingLists", []):
        if sl["name"] == shopping_list_name:
            list_id = sl["id"]
            break
    if not list_id:
        print(f"Shopping list '{shopping_list_name}' not found", file=sys.stderr)
        sys.exit(1)

    all_items = []
    for name in recipe_names:
        recipe_id = None
        for r in overview.get("recipes", []):
            if r["name"] == name:
                recipe_id = r["id"]
                break
        if recipe_id:
            data = await og.get_list_items(recipe_id)
            all_items.extend(data["list"]["items"])
        else:
            print(f"Warning: recipe '{name}' not found", file=sys.stderr)

    if not all_items:
        print("No items to add", file=sys.stderr)
        return

    items = [
        (item["value"], item.get("categoryId"), item.get("note"))
        for item in all_items
    ]
    await og.add_items_to_list(list_id, items)
    print(f"Added {len(items)} items from {len(recipe_names)} recipes to '{shopping_list_name}'")


async def main():
    if len(sys.argv) < 2:
        print("Usage: ourgroceries_tool.py <command> [args...]", file=sys.stderr)
        print("Commands:", file=sys.stderr)
        print("  categories              List available categories", file=sys.stderr)
        print("  add-recipe <file>       Add recipe from JSON file (use - for stdin)", file=sys.stderr)
        print("  list-recipes            List all recipe names", file=sys.stderr)
        print("  list-shopping-lists     List all shopping list names", file=sys.stderr)
        print("  append-recipes <list> <json_names>  Append items from recipes to a shopping list", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "categories":
        await categories()
    elif cmd == "add-recipe":
        if len(sys.argv) < 3:
            print("Usage: ourgroceries_tool.py add-recipe <file>", file=sys.stderr)
            print("  file: path to JSON file, or - for stdin", file=sys.stderr)
            sys.exit(1)
        src = sys.argv[2]
        if src == "-":
            recipe = json.loads(sys.stdin.read())
        else:
            with open(src) as f:
                recipe = json.load(f)
        await add_recipe(recipe)
    elif cmd == "list-recipes":
        await list_recipes()
    elif cmd == "list-shopping-lists":
        await list_shopping_lists()
    elif cmd == "append-recipes":
        if len(sys.argv) < 4:
            print("Usage: ourgroceries_tool.py append-recipes <shopping_list_name> <recipe_names_json>", file=sys.stderr)
            sys.exit(1)
        shopping_list_name = sys.argv[2]
        recipe_names = json.loads(sys.argv[3])
        await append_recipes(shopping_list_name, recipe_names)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
