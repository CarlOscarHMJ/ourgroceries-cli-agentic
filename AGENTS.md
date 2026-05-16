# Agent Instructions: Recipe → OurGroceries

Credentials and settings are read from `.env`. Never reveal or expose these values.
You can add recipes as shopping lists to OurGroceries.

## Language

The `LANGUAGE` variable in `.env` sets the language for all recipe content.
All recipe names, notes, and ingredient names must be in the configured language.

Currently: **Danish**

## Title formatting

Recipe names are sorted alphabetically in the app. Put the
most characteristic ingredient first so similar recipes group
together.

✅ "Fennikel- og æblesalat med ovnristede kikærter 🥗"
❌ "Sprød fennikel- og æblesalat med ovnristede kikærter 🥗"

Drop decorative adjectives at the start — they ruin sorting.

## Workflow

1. User gives you recipe info (text, file, URL, etc.)
2. Parse out the **recipe name** and **ingredients list**
3. Add a **meaningful emoji** to the end of the recipe name
4. Look up available categories using the tool
5. Match each ingredient to a category
6. Create the recipe list via the tool

## Tools

### List available categories
```bash
python3 ourgroceries_tool.py categories
```
Output: `CategoryName|categoryId` (one per line)

### Add a recipe
Create a JSON file in the current folder `recipe.json` with this structure:

```json
{
  "name": "Recipe Name",
  "note": "Steg løg og hvidløg. Tilsæt tomater og kog i 20 min.",
  "ingredients": [
    {"name": "Milk", "category": "Mejeri", "note": "3.5%"},
    {"name": "Bread", "category": "Brød"},
    {"name": "Eggs", "category": "Mejeri"},
    {"name": "Tomatoes", "category": "Frugt Og Grønt"},
    {"name": "Salt"}
  ]
}
```

Then run:
```bash
python3 ourgroceries_tool.py add-recipe recipe.json
```

Then remove the `recipe.json` file

Notes:
- `category` must match a category name from `categories` output (case-sensitive)
- Omit `category` or use `""` for uncategorized items
- `"name"` should include the quantity in parentheses, e.g. `"Æbler (3)"` not `"Æbler"` with a note.
  Only the number goes in parentheses — no descriptors. Descriptors like "sprød",
  "store", "frisk" go BEFORE the ingredient name: `"Sprøde æbler (3)"`.
  Units go AFTER the name with "i" prefix: `"Valnødder i g (100)"`, `"Mælk i dl (3)"`.
  Only use `"note"` for actual extra info (e.g. økologisk, friskrevet), not for quantity.
- Ingredient names must be in **plural form** (e.g. "Æbler" not "Æble").
- Fix common misspellings: "avocado" (not "avokado"), "chili" (not "chilli"),
  "parmesan" (not "parmasan"), "mozzarella" (not "mozerella").
- Omit words like "lidt", "en", "et", "noget" from ingredient names.
- `"note"` at the root level is the recipe instructions — added as a 📝 item
  Write it as a numbered list, e.g. "1. Pisk æg og sukker. 2. Tilsæt mælk. 3. Steg på panden." add newline between each point
- Scale the recipe to **3 adults** unless otherwise stated. Begin the note with the
  portion count, e.g. "3 personer. 1. Pisk æg og sukker. 2. ..."
- If a list with the same name already exists, it will be replaced

## Add to shopping list

1. Run `ourgroceries_tool.py list-recipes` to show the user all available recipes
2. Fuzzy-match the user's input against recipe names
3. Present the matching recipe names and ask the user for confirmation
4. If confirmed, run:
   ```bash
   python3 ourgroceries_tool.py append-recipes "Indkøb i DK 🇩🇰🥺👩🏽‍🤝‍👨🏼" '["Recipe Name 1", "Recipe Name 2"]'
   ```
   Use the exact shopping list name shown by `list-recipes`.
   Pass recipe names as a JSON array string.
5. If not confirmed, tell the user to rewrite and try again
6. Never delete items already in the shopping list — only append
