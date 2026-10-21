"""Seasonal cooking: recipes from what the garden gives."""

from __future__ import annotations

from datetime import date
import re

from custom_components.garden_manager.engine import cooking
from custom_components.garden_manager.engine.plantdb import PlantDatabase

READY = ["tomato", "courgette", "kale", "carrot", "leek", "basil", "pumpkin", "potato", "lettuce", "cucumber", "apple"]


def _produce(db: PlantDatabase, ids=READY):
    return cooking.ready_produce(
        [{"plant_id": i, "until": f"2026-08-{10 + n}", "bed": "b1"} for n, i in enumerate(ids)], db
    )


def test_kitchen_kinds(db: PlantDatabase) -> None:
    kind = lambda pid: cooking.produce_kind(db.get(pid))  # noqa: E731
    assert kind("carrot") == "root" and kind("kale") == "brassica" and kind("pumpkin") == "squash"
    assert kind("potato") == "potato" and kind("leek") == "allium" and kind("basil") == "herb"
    assert kind("raspberry_summer") == "fruit" and kind("tomato") == "fruiting"
    assert kind("lavender") is None and kind("calendula") is None and kind("chili_pepper") is None


def test_suggestions_put_the_garden_first(db: PlantDatabase) -> None:
    prefs = cooking.Prefs.from_dict({"proteins": ["chicken", "mince"], "servings": 4, "use": ["feta"]})
    recipes = cooking.suggest(_produce(db), db, prefs, "nl", limit=14)
    assert len(recipes) >= 10
    assert len({r["id"] for r in recipes}) == len(recipes)
    techniques = {r["technique"] for r in recipes}
    assert {"soup", "starter", "main", "dessert"} <= {r["course"] for r in recipes}  # spread over the chapters
    assert len(techniques) >= 8  # and over many kinds of dish
    for r in recipes:
        garden = [i for i in r["ingredients"] if i["source"] == "garden"]
        assert garden, r["title"]
        assert all(i["group"] != "garden" for i in r["shopping"])
        assert r["steps"] and r["servings"] == 4
        if not cooking.TECHNIQUE[r["technique"]].raw:  # lettuce and cucumber are eaten raw
            assert not {"lettuce", "cucumber"} & {i["id"] for i in garden}, r["title"]
        if r["course"] in ("dessert", "preserve"):
            assert r["spec"]["protein"] == ""
        else:  # a dish made for certain proteins may go without
            assert r["spec"]["protein"] in ("chicken", "mince") or cooking.TECHNIQUE[r["technique"]].strict
        feta = any(i["id"] == "feta" for i in r["ingredients"])
        assert feta == (
            r["technique"] in {"soup", "cold_soup", "crostini", "roast", "salad", "pasta", "frittata", "stuffed"}
        ), r["title"]
        if feta:  # taken from the fridge: in the house, never on the shopping list
            assert next(i for i in r["ingredients"] if i["id"] == "feta")["source"] == "pantry"


def test_side_and_servings_change_the_recipe(db: PlantDatabase) -> None:
    spec = {"technique": "stir_fry", "produce": ["kale", "carrot"], "side": "rice", "protein": "beef", "servings": 2}
    two = cooking.render(spec, db, "en")
    four = cooking.render({**spec, "servings": 4, "side": "noodles"}, db, "en")
    assert two and four and two["id"] != four["id"]
    rice = next(i for i in two["ingredients"] if i["id"] == "rice")
    assert rice["qty"] == 150 and rice["source"] == "shop"
    assert any(i["id"] == "noodles" for i in four["ingredients"])
    beef = lambda r: next(i for i in r["ingredients"] if i["id"] == "beef")["qty"]  # noqa: E731
    assert beef(four) == 2 * beef(two)
    assert two["title"] == "Stir-fried kale and carrot" and two["subtitle"] == "with beef (steak strips)"


def test_what_is_in_the_house_is_not_bought(db: PlantDatabase) -> None:
    spec = {"technique": "risotto", "produce": ["pumpkin"], "side": "rice", "servings": 2}
    recipe = cooking.render(spec, db, "fr", pantry=["rice", "parmesan", "butter"])
    assert recipe is not None
    bought = {i["id"] for i in recipe["shopping"]}
    assert "rice" not in bought and "parmesan" not in bought and "stock" in bought
    assert "vegetarian" in recipe["tags"]
    # the garden's own onion replaces the bought one
    with_onion = cooking.render({**spec, "produce": ["pumpkin", "onion"]}, db, "en")
    assert with_onion and "onion" not in {i["id"] for i in with_onion["ingredients"] if i["source"] != "garden"}


def test_shopping_list_adds_up(db: PlantDatabase) -> None:
    a = cooking.render({"technique": "pasta", "produce": ["tomato"], "side": "pasta", "servings": 2}, db, "nl")
    b = cooking.render({"technique": "pasta", "produce": ["courgette"], "side": "pasta", "servings": 2}, db, "nl")
    lst = cooking.shopping_list([a, b], "nl")
    pasta = next(r for r in lst["buy"] if r["id"] == "pasta")
    assert pasta["qty"] == 360 and pasta["label"] == "360 g"
    assert {r["id"] for r in lst["garden"]} == {"tomato", "courgette"}
    text = cooking.shopping_text([a, b], "nl")
    assert text.startswith("Boodschappenlijst") and "pasta (360 g)" in text


def test_unknown_spec_is_refused(db: PlantDatabase) -> None:
    assert cooking.render({"technique": "boil", "produce": ["kale"]}, db) is None
    assert cooking.render({"technique": "soup", "produce": ["lavender"]}, db) is None


def test_pdfs(db: PlantDatabase) -> None:
    recipes = cooking.suggest(_produce(db), db, cooking.Prefs(), "en", limit=3)
    for kind in ("recipe", "book", "shopping"):
        pdf = cooking.recipes_pdf(recipes, "en", kind, today=date(2026, 8, 1))
        assert pdf.startswith(b"%PDF") and len(pdf) > 1500
    assert cooking.recipes_pdf(recipes, "nl", "book").count(b"/Type /Page ") >= 5


def test_unreadable_input_falls_back(db: PlantDatabase) -> None:
    prefs = cooking.Prefs.from_dict({"servings": "x", "pantry": "rice", "proteins": [1, "beef"], "side": 3})
    assert prefs.servings == 2 and prefs.pantry == [] and prefs.proteins == ["beef"] and prefs.side == ""
    assert cooking.Prefs.from_dict(["nope"]).servings == 2  # type: ignore[arg-type]
    assert cooking.render({"technique": "soup", "produce": ["carrot"], "servings": "many"}, db)["servings"] == 2
    assert cooking.render(["soup"], db) is None  # type: ignore[arg-type]
    assert cooking.render({"technique": "soup", "produce": 1}, db) is None
    odd = cooking.render({"technique": "soup", "produce": ["carrot", {}], "extras": [{}, "lemon", 3]}, db)
    assert odd is not None and [i["plant_id"] for i in odd["ingredients"] if i.get("group") == "garden"] == ["carrot"]
    assert cooking.str_ids("carrot") == [] and cooking.str_ids(("a", 1)) == ["a"]


def test_fridge_items_only_go_where_they_fit(db: PlantDatabase) -> None:
    fridge = ["grated_cheese", "yoghurt", "parmesan"]
    pasta = cooking.render(
        {"technique": "pasta", "produce": ["courgette"], "side": "pasta", "extras": fridge}, db, "nl"
    )
    assert pasta is not None and pasta["spec"]["extras"] == []  # no yoghurt on pasta; parmesan is in it already
    assert not any("yoghurt" in s for s in pasta["steps"])
    assert next(i for i in pasta["ingredients"] if i["id"] == "parmesan")["source"] == "shop"
    roast = cooking.render({"technique": "roast", "produce": ["carrot", "pumpkin"], "extras": fridge}, db, "nl")
    assert roast is not None and sorted(roast["spec"]["extras"]) == ["grated_cheese", "yoghurt"]  # one cheese is enough
    assert any("kaaskorstje" in s for s in roast["steps"])
    assert {i["id"]: i["source"] for i in roast["ingredients"]}["yoghurt"] == "pantry"
    assert cooking.fitting_extras("stir_fry", fridge) == ["yoghurt"]  # as a dip, no cheese
    assert cooking.fitting_extras("plate", ["cream"], has_protein=False) == []
    tofu = cooking.render({"technique": "plate", "produce": ["kale"], "protein": "tofu", "extras": ["cream"]}, db, "en")
    assert tofu is not None and tofu["spec"]["extras"] == []  # no meat pan to make a cream sauce in
    steak = cooking.render(
        {"technique": "plate", "produce": ["kale"], "protein": "steak", "extras": ["cream"]}, db, "en"
    )
    assert steak is not None and steak["spec"]["extras"] == ["cream"]
    # "for the last 8 minutes" is said before the oven step it times, not after it
    eggs = cooking.render({"technique": "roast", "produce": ["carrot", "pumpkin"], "extras": ["eggs"]}, db, "en")
    assert eggs is not None
    at = lambda word: next(n for n, s in enumerate(eggs["steps"]) if word in s)  # noqa: E731
    assert at("crack the eggs") < at("Roast for 30-35 minutes")
    assert cooking.fitting_extras("stew", ["cream", "yoghurt"]) == ["yoghurt"]  # coconut milk is the cream there
    assert cooking.fitting_extras("stoemp", ["cream", "mustard"]) == ["mustard", "cream"]
    assert cooking.fitting_extras("frittata", ["milk", "cream"]) == ["milk"]  # one is enough
    assert cooking.fitting_extras("stuffed", ["parmesan", "feta"]) == ["feta"]  # one extra cheese
    assert cooking.fitting_extras("roast", ["parmesan"]) == ["parmesan"]
    assert cooking.fitting_extras("gratin", ["parmesan"]) == ["parmesan"]  # mixed into the crust
    assert cooking.fitting_extras("soup", ["garlic"], produce=["pumpkin", "garlic"]) == []  # the garden gives it
    assert cooking.fitting_extras("pasta", ["onion"], produce=["tomato", "leek"]) == []
    assert cooking.fitting_extras("soup", ["garlic"], produce=["pumpkin"]) == ["garlic"]
    # an early step goes in after the vegetables are in the pan, not at the end
    sauce = cooking.render(
        {"technique": "pasta", "produce": ["tomato"], "side": "pasta", "extras": ["cream"]}, db, "en"
    )
    assert sauce is not None
    assert sauce["steps"].index(next(s for s in sauce["steps"] if "creamy sauce" in s)) < len(sauce["steps"]) - 2


def test_every_dish_its_own_idea(db: PlantDatabase) -> None:
    """Yoghurt (and the rest of the fridge) is worked in differently per dish, not just spooned on."""
    yog = lambda t, produce, herbs=(): next(  # noqa: E731
        s
        for s in cooking.render({"technique": t, "produce": produce, "extras": ["yoghurt"]}, db, "nl", list(herbs))[
            "steps"
        ]
        if "yoghurt" in s
    )
    assert "sojasaus" in yog("stir_fry", ["kale"]) or "currypasta" in yog("stir_fry", ["kale"])
    assert "dille" in yog("stew", ["pumpkin", "carrot"], ["dille"])  # fresh garden herbs go in
    assert "rozemarijn" not in yog("roast", ["carrot", "pumpkin"], ["rozemarijn"])  # not in a cold sauce
    # across dishes the same item gets different preparations
    texts = {
        yog(t, p)
        for t, p in [
            ("roast", ["carrot"]),
            ("roast", ["pumpkin"]),
            ("roast", ["tomato"]),
            ("roast", ["potato"]),
            ("salad", ["lettuce"]),
            ("stew", ["pumpkin"]),
            ("dessert", ["apple"]),
            ("soup", ["leek"]),
        ]
    }
    assert len(texts) >= 6
    # every listed preparation exists in every language and names its item or stands on its own
    from custom_components.garden_manager.engine import cooking_extras as x

    for tech, items in x.USES.items():
        assert tech in cooking.TECHNIQUE
        for item, keys in items.items():
            assert item in cooking.PANTRY, item
            for key in keys:
                where, *texts = x.PREP[key]
                assert where in ("early", "mid", "during", "late") and len(texts) == 3 and all(texts), key


def test_the_cooks_own_version(db: PlantDatabase) -> None:
    recipe = cooking.render({"technique": "soup", "produce": ["pumpkin"], "servings": 2}, db, "nl")
    assert recipe is not None
    rows = [r for n, x in enumerate([{"name": "Pompoen", "qty": 600, "unit": "g", "source": "garden", "plant_id": "pumpkin"},
                                     {"name": "Gember", "qty": 1, "unit": "pc", "source": "shop"}, {"name": " "}, "x"])
            if (r := cooking.custom_ingredient(x, n)) is not None]  # fmt: skip
    assert (
        [r["name"] for r in rows] == ["Pompoen", "Gember"]
        and rows[1]["id"].startswith("custom-")
        and rows[1]["group"] == "other"
    )
    own = cooking.apply_custom(dict(recipe), rows, ["Alles in de pot.", "Mixen."], "nl")
    assert own["custom"] and own["steps"] == ["Alles in de pot.", "Mixen."]
    assert [i["name"] for i in own["shopping"]] == ["Gember"]
    assert [i["name"] for i in own["ingredients"] if i["source"] != "basic"] == ["Pompoen", "Gember"]
    assert cooking.shopping_list([own], "nl")["buy"][0]["name"] == "Gember"
    assert cooking.apply_custom(dict(recipe), [], [], "nl")["custom"] is False


def test_chapters_soups_starters_mains_desserts(db: PlantDatabase) -> None:
    recipes = cooking.suggest(_produce(db), db, cooking.Prefs.from_dict({"proteins": ["chicken"]}), "nl", limit=12)
    courses = [r["course"] for r in recipes]
    assert set(cooking.MEAL_COURSES) <= set(courses)  # every chapter of a meal gets ideas
    assert courses == sorted(courses, key=cooking.COURSES.index)  # soups first, desserts last, preserving after
    assert {"Soepen", "Voorgerechten", "Hoofdgerechten", "Desserten"} <= {r["course_name"] for r in recipes}
    assert cooking.course_of("salad") == "starter" and cooking.course_of("salad", "chicken") == "main"
    assert cooking.course_of("pesto", side="bread") == "starter" and cooking.course_of("pesto", side="pasta") == "main"
    assert cooking.course_of("cold_soup") == "soup" and cooking.course_of("compote") == "dessert"
    crostini = cooking.render(
        {"technique": "crostini", "produce": ["tomato"], "side": "bread", "extras": ["feta"]}, db, "en"
    )
    assert crostini is not None and crostini["course"] == "starter"
    assert not any(s.startswith("Toast the bread or warm it") for s in crostini["steps"])  # the toasts are the dish
    assert any("spread" in s for s in crostini["steps"])
    cold = cooking.render({"technique": "cold_soup", "produce": ["tomato", "cucumber"]}, db, "en")
    assert cold is not None and cold["course"] == "soup"  # cucumber may go raw in a chilled soup
    pdf = cooking.recipes_pdf(recipes, "nl", "book", today=date(2026, 8, 1))
    assert pdf.count(b"/Type /Page ") >= len(recipes) + 1 + 4 + 1  # cover, 4 chapter pages, recipes, shopping list


def test_new_dishes_hold_together(db: PlantDatabase) -> None:
    plate = cooking.fitting_extras("plate", ["cream", "white_wine"], produce=["kale"])
    assert plate in (["cream"], ["white_wine"])  # one pan sauce, not two
    toasts = cooking.render(
        {"technique": "crostini", "produce": ["tomato"], "side": "", "extras": ["lemon", "nuts"]}, db, "en"
    )
    assert toasts is not None and any(i["id"] == "bread" for i in toasts["shopping"])  # always their bread
    assert not any("pasta" in s.lower() for s in toasts["steps"])
    prefs = cooking.Prefs.from_dict({"side": "none"})
    crostini = [r for r in cooking.suggest(_produce(db), db, prefs, "en", 20) if r["technique"] == "crostini"]
    assert all(r["spec"]["side"] == "bread" for r in crostini)
    sweet = cooking.render({"technique": "compote", "produce": ["apple"], "extras": ["honey"]}, db, "en")
    assert sweet is not None
    at = lambda word: next(n for n, s in enumerate(sweet["steps"]) if word in s)  # noqa: E731
    assert at("instead of the sugar") < at("Simmer it gently")  # said before the fruit simmers
    cold = cooking.render({"technique": "cold_soup", "produce": ["tomato"]}, db, "en")
    assert cold is not None and cold["minutes"] >= 45  # the chilling counts


# --------------------------------------------------------------------------- #
# The dishes of cooking_dishes, the chapter on preserving and the menus
# --------------------------------------------------------------------------- #
def _fitting_plants(db: PlantDatabase, tech: cooking.Technique) -> list[str]:
    """Garden plants a technique takes, as ids of the plant database."""
    ids = []
    for plant in db.all():
        kind = cooking.produce_kind(plant)
        if kind not in tech.kinds or (tech.plants and plant.id not in tech.plants):
            continue
        if plant.id in cooking.RAW_ONLY and not tech.raw:
            continue
        ids.append(plant.id)
    return ids


def test_every_dish_reads_well_in_every_language(db: PlantDatabase) -> None:
    for tech in cooking.TECHNIQUES:
        ids = _fitting_plants(db, tech)
        assert ids, tech.id
        assert all(item in cooking.PANTRY for item in tech.staples), tech.id
        assert tech.sides == () or all(side in cooking.SIDES for side in tech.sides), tech.id
        for lang in ("en", "nl", "fr"):
            assert len(cooking._STEPS[lang][tech.id]) == len(cooking._STEPS["en"][tech.id]) >= 3, (tech.id, lang)
            # a herb dish needs its herb; the others take a vegetable or fruit first
            pick = ids[:1]
            if tech.needs_herb:
                pick = [i for i in ids if cooking.produce_kind(db.get(i)) == "herb"][:1]
            if tech.needs_main:  # ... and a vegetable or fruit besides
                pick += [i for i in ids if cooking.produce_kind(db.get(i)) != "herb"][:1]
            recipe = cooking.render({"technique": tech.id, "produce": pick, "servings": 4}, db, lang)
            assert recipe is not None, (tech.id, lang)
            text = " ".join([recipe["title"], recipe["technique_name"], *recipe["steps"]])
            assert "{" not in text and "}" not in text, (tech.id, lang, text)
            assert recipe["course"] == (tech.course or recipe["course"])
            assert recipe["course"] in cooking.COURSES and recipe["course_name"]


def test_dishes_made_for_certain_plants_refuse_the_others(db: PlantDatabase) -> None:
    assert cooking.render({"technique": "cake", "produce": ["tomato"]}, db) is None
    assert cooking.render({"technique": "cake", "produce": ["carrot"]}, db) is not None
    assert cooking.render({"technique": "passata", "produce": ["courgette"]}, db) is None
    assert cooking.render({"technique": "passata", "produce": ["tomato"], "servings": 4}, db) is not None
    assert cooking.render({"technique": "sauerkraut", "produce": ["lettuce"]}, db) is None
    # a garden herb never spoils a dish: it is only scattered over it
    assert cooking.render({"technique": "ratatouille", "produce": ["tomato", "aubergine", "basil"]}, db) is not None


def test_preserving_is_a_chapter_of_its_own(db: PlantDatabase) -> None:
    passata = cooking.render({"technique": "passata", "produce": ["tomato"], "servings": 4}, db, "en")
    assert passata["course"] == "preserve" and passata["course_name"] == "Preserving & pickles"
    assert passata["ingredients"][0]["qty"] >= 2000  # a batch, not one plate
    assert cooking.course_name("preserve", "nl") == "Bewaren & inmaken"
    ideas = cooking.suggest(_produce(db), db, cooking.Prefs.from_dict({}), "nl", limit=9)
    preserve = [r for r in ideas if r["course"] == "preserve"]
    assert 1 <= len(preserve) <= 2 and ideas[-len(preserve) :] == preserve  # after the meal, never crowding it out
    assert len([r for r in ideas if r["course"] != "preserve"]) == 9
    book = cooking.recipes_pdf(ideas, "nl")
    assert book.startswith(b"%PDF")
    assert all(
        not i["fridge"] for i in cooking.catalog("en")["pantry"] if i["id"] in ("tahini", "gelatine", "soup_pasta")
    )
    assert next(i for i in cooking.catalog("en")["pantry"] if i["id"] == "feta")["fridge"] is True


def test_flemish_asparagus_and_waterzooi(db: PlantDatabase) -> None:
    assert cooking.course_of("flemish") == "starter" and cooking.course_of("flemish", "ham") == "main"
    water = cooking.render(
        {"technique": "waterzooi", "produce": ["leek", "carrot"], "protein": "chicken", "side": "potatoes"}, db, "en"
    )
    assert any("Poach" in s for s in water["steps"]) and not any("hot pan" in s for s in water["steps"])
    assert water["subtitle"] == "with chicken breast"


def test_grain_dishes_keep_their_grain(db: PlantDatabase) -> None:
    tab = cooking.render({"technique": "tabbouleh", "produce": ["parsley", "tomato"], "side": "pasta"}, db, "en")
    assert tab["spec"]["side"] == "bulgur"  # a tabbouleh is made with bulgur, whatever side was asked
    none = cooking.render({"technique": "rolls", "produce": ["savoy_cabbage"], "side": ""}, db, "en")
    assert none["spec"]["side"] == "rice"
    cake = cooking.render({"technique": "cake", "produce": ["carrot"], "side": "rice", "protein": "beef"}, db, "en")
    assert cake["spec"]["side"] == "" and not any(i["id"] in ("rice", "beef") for i in cake["ingredients"])


def test_menus_are_three_courses_that_belong_together(db: PlantDatabase) -> None:
    ids = [
        "tomato",
        "courgette",
        "aubergine",
        "sweet_pepper",
        "basil",
        "parsley",
        "cucumber",
        "strawberry",
        "raspberry_summer",
        "carrot",
    ]
    prefs = cooking.Prefs.from_dict({"proteins": ["chicken"], "servings": 4})
    menus = cooking.menus(_produce(db, ids), db, prefs, "nl", 5, date(2026, 8, 10))
    assert len(menus) >= 4
    assert menus[0]["theme"]  # the season's themed menus come first
    seen: set[str] = set()
    for menu in menus:
        assert [c["course"] for c in menu["courses"]][1:] == ["main", "dessert"]
        assert menu["courses"][0]["course"] in ("soup", "starter")
        recipes = [c["recipe"] for c in menu["courses"]]
        assert menu["minutes"] == sum(r["minutes"] for r in recipes) and menu["servings"] == 4
        assert not seen & {r["id"] for r in recipes}, menu["title"]  # a dish is in one menu only
        seen |= {r["id"] for r in recipes}
        assert all(set(r["spec"]["produce"]) <= set(ids) for r in recipes)
    titles = {m["title"] for m in menus}
    assert "Provençaals tuinmenu" in titles or "Siciliaanse avond" in titles
    plain = cooking.menus(_produce(db, ["kale", "potato", "leek", "apple"]), db, prefs, "en", 3, date(2026, 1, 10))
    assert plain and all(m["title"] for m in plain)
    assert cooking.menus([], db, prefs, "en") == []


def test_a_themed_menu_needs_its_produce(db: PlantDatabase) -> None:
    prefs = cooking.Prefs.from_dict({})
    winter = cooking.menus(
        _produce(db, ["kale", "carrot", "leek", "potato", "apple"]), db, prefs, "en", 6, date(2026, 8, 1)
    )
    assert "Courgette glut menu" not in {m["title"] for m in winter}  # no courgette in the garden
    summer = cooking.menus(
        _produce(db, ["courgette", "basil", "strawberry", "tomato"]), db, prefs, "en", 6, date(2026, 8, 1)
    )
    assert {m["theme"] for m in summer} & {"courgette", "tomato", "provence"}


# --------------------------------------------------------------------------- #
# Findings of the whole-repository review
# --------------------------------------------------------------------------- #
def test_nothing_is_offered_raw_that_must_be_cooked(db: PlantDatabase) -> None:
    for tech in ("sorbet", "cups", "panna_cotta", "salad", "carpaccio", "crostini"):
        for plant in ("elderberry", "bush_bean", "runner_bean"):
            assert cooking.render({"technique": tech, "produce": [plant]}, db) is None, (tech, plant)
    assert cooking.render({"technique": "fool", "produce": ["elderberry"]}, db) is not None  # cooked
    assert cooking.render({"technique": "pasta", "produce": ["bush_bean"]}, db) is not None
    prefs = cooking.Prefs.from_dict({"servings": 2})
    ideas = cooking.suggest(_produce(db, ["elderberry", "bush_bean", "lettuce", "strawberry"]), db, prefs, "en", 30)
    for r in ideas:
        if r["technique"] in cooking._UNCOOKED:
            assert not {"elderberry", "bush_bean"} & set(r["spec"]["produce"]), r["title"]


def test_a_dish_needs_its_main_ingredient_not_just_herbs(db: PlantDatabase) -> None:
    for tech, herbs in (
        ("flemish", ["parsley"]),
        ("cob", ["parsley"]),
        ("caprese", ["basil"]),
        ("tabbouleh", ["parsley", "peppermint"]),
    ):
        assert cooking.render({"technique": tech, "produce": herbs}, db) is None, tech
    prefs = cooking.Prefs.from_dict({})
    only_parsley = cooking.suggest(_produce(db, ["parsley"]), db, prefs, "en", 30)
    assert not {r["technique"] for r in only_parsley} & {"flemish", "cob", "tabbouleh", "caprese"}
    only_basil = cooking.suggest(_produce(db, ["basil"]), db, prefs, "en", 30)
    assert "caprese" not in {r["technique"] for r in only_basil}
    assert any(r["technique"] == "herb_cubes" for r in only_basil)  # herbs alone can be frozen as pesto cubes


def test_more_suitable_vegetables_never_remove_a_dish(db: PlantDatabase) -> None:
    prefs = cooking.Prefs.from_dict({})
    five = ["tomato", "cherry_tomato", "courgette", "aubergine", "sweet_pepper"]
    ideas = cooking.suggest(_produce(db, five), db, prefs, "en", 40)
    assert {"ratatouille", "tian"} <= {r["technique"] for r in ideas}
    rata = next(r for r in ideas if r["technique"] == "ratatouille")
    assert len(rata["spec"]["produce"]) == 4  # distinct kinds first, then the rest fills the places
    assert cooking.suggest(_produce(db, five[:2]), db, prefs, "en", 40)  # two of a kind still make dishes


def test_a_dish_keeps_the_grain_and_cooks_it_once(db: PlantDatabase) -> None:
    prefs = cooking.Prefs.from_dict({"side": "none", "servings": 2})
    ideas = cooking.suggest(_produce(db, ["pumpkin", "carrot", "potato", "kale", "tomato"]), db, prefs, "en", 40)
    for r in ideas:
        if r["technique"] in ("risotto", "pasta", "stoemp", "stuffed"):
            ids = {i["id"] for i in r["ingredients"]}
            assert ids & {"rice", "pasta", "gnocchi", "potatoes", "bulgur", "couscous"}, r["title"]
    risotto = cooking.render({"technique": "risotto", "produce": ["pumpkin"], "side": "rice"}, db, "en")
    assert sum("rice" in s.lower() for s in risotto["steps"]) == 1  # toasted in the method, not cooked before
    assert not any("as on the pack" in s for s in risotto["steps"])
    stoemp = cooking.render({"technique": "stoemp", "produce": ["kale"], "side": "potatoes"}, db, "en")
    assert sum("Boil the potatoes" in s for s in stoemp["steps"]) == 1


def test_dry_lentils_are_cooked(db: PlantDatabase) -> None:
    recipe = cooking.render({"technique": "soup", "produce": ["carrot"], "protein": "lentils"}, db, "en")
    assert any("simmer them in plenty of unsalted water" in s for s in recipe["steps"])


def test_the_cooks_own_quantities_and_ingredients_stay_as_typed() -> None:
    saffron = cooking.custom_ingredient({"name": "Saffron", "qty": 1, "unit": "g"}, 3)
    spice = cooking.custom_ingredient({"name": "Spice", "qty": 0.25, "unit": "tbsp"}, 4)
    assert saffron["qty"] == 1 and spice["qty"] == 0.25
    a = cooking.custom_ingredient({"name": "Mushrooms", "qty": 100, "unit": "g", "source": "shop"}, 8)
    b = cooking.custom_ingredient({"name": "Olives", "qty": 50, "unit": "g", "source": "shop"}, 8)
    assert a["id"] != b["id"] and a["id"].startswith("custom-")
    again = cooking.custom_ingredient({"name": " mushrooms ".strip().upper(), "qty": 1, "unit": "g"}, 0)
    assert again["id"] == a["id"]  # the same thing is one thing, wherever it sits
    kept = cooking.custom_ingredient({"id": "tomato", "name": "Tomato", "qty": 1, "unit": "g"}, 0)
    assert kept["id"] == "tomato"
    lst = cooking.shopping_list([{"ingredients": [a]}, {"ingredients": [b]}], "en")
    assert {r["name"] for r in lst["buy"]} == {"Mushrooms", "Olives"}


def test_what_a_preparation_needs_joins_the_ingredients(db: PlantDatabase) -> None:
    spec = {"technique": "roast", "produce": ["carrot", "pumpkin"], "extras": ["yoghurt"]}
    for produce in (["carrot", "pumpkin"], ["carrot", "pumpkin", "beetroot"], ["pumpkin"], ["carrot"]):
        recipe = cooking.render({**spec, "produce": produce}, db, "en", [], [])
        ids = {i["id"] for i in recipe["ingredients"]}
        key = cooking._plan_extras("roast", ["yoghurt"], False, produce)["yoghurt"]
        for need in cooking._x.DEPENDS.get(key, ()):
            assert need in ids, (key, need)
            assert next(i for i in recipe["ingredients"] if i["id"] == need)["source"] == "shop"
    honey = cooking.render({**spec, "produce": ["carrot", "pumpkin", "beetroot"]}, db, "en", [], ["honey", "mustard"])
    assert all(i["source"] == "pantry" for i in honey["ingredients"] if i["id"] in ("honey", "mustard"))


def test_a_long_recipe_continues_on_another_page(db: PlantDatabase) -> None:
    recipe = cooking.render({"technique": "soup", "produce": ["pumpkin"]}, db, "en")
    short = cooking.recipes_pdf([recipe], "en", "recipe")
    long = dict(recipe, steps=[f"Step {n}: " + "stir gently and wait a little longer. " * 8 for n in range(1, 31)])
    longer = cooking.recipes_pdf([long], "en", "recipe")
    pages = lambda pdf: len(re.findall(rb"/Type\s*/Page\b(?!s)", pdf))  # noqa: E731
    assert pages(longer) > pages(short)


def test_review_round_two(db: PlantDatabase) -> None:
    # the garden's mint reaches the sauces
    assert {"peppermint", "spearmint", "apple_mint"} <= set(cooking._SAUCE_HERBS) and "mint" not in cooking._SAUCE_HERBS
    # shelling beans are not offered in a green soup that cooks them for minutes
    assert cooking.render({"technique": "green_soup", "produce": ["borlotti_bean"]}, db) is None
    assert cooking.render({"technique": "green_soup", "produce": ["runner_bean"]}, db) is None
    assert cooking.render({"technique": "green_soup", "produce": ["pea"]}, db) is not None
    # what these preparations name (garlic, lemon, vinegar) is on the list
    for key in ("soup_yog_garlic", "soup_crumbs", "salad_crumbs", "soup_feta_lemon", "feta_whip", "stew_yog_lemon",
                "frittata_yog", "pasta_cream", "salad_egg_poached"):  # fmt: skip
        assert key in cooking._x.DEPENDS, key
    # a step longer than the room left on the page starts a new one
    recipe = cooking.render({"technique": "soup", "produce": ["pumpkin"]}, db, "en")
    steps = ["Short step."] * 22 + ["word " * 110]
    page_count = lambda r: len(re.findall(rb"/Type\s*/Page\b(?!s)", cooking.recipes_pdf([r], "en", "recipe")))  # noqa: E731
    assert page_count(dict(recipe, steps=steps)) > page_count(dict(recipe, steps=steps[:22]))
