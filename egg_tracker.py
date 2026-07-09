import json
import os
from datetime import datetime

DATA_FILE = "egg_data.json"
DEFAULT_PEOPLE = ["Person 1", "Person 2", "Person 3", "Person 4"]


def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "people": DEFAULT_PEOPLE,
            "purchases": [],
            "consumptions": [],
        }

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def ask_people(data):
    if data["people"] != DEFAULT_PEOPLE:
        return

    print("Enter the four people in your flat. Press Enter to keep defaults.")
    print("Separate names by commas, for example: Alice,Bob,Charlie,Dana")
    raw = input("Names: ").strip()
    if raw:
        names = [name.strip() for name in raw.split(",") if name.strip()]
        if len(names) == 4:
            data["people"] = names
        else:
            print("Please enter exactly 4 names. Keeping default names.")


def choose_person(data, prompt):
    people = data["people"]
    print(prompt)
    for idx, person in enumerate(people, start=1):
        print(f"  {idx}. {person}")

    while True:
        selection = input("Choose a person by number: ").strip()
        if selection.isdigit():
            index = int(selection) - 1
            if 0 <= index < len(people):
                return people[index]
        print("Invalid selection. Please enter a valid number.")


def ask_positive_int(label):
    while True:
        value = input(f"{label}: ").strip()
        if value.isdigit() and int(value) > 0:
            return int(value)
        print("Please enter a whole number greater than 0.")


def ask_positive_float(label):
    while True:
        value = input(f"{label}: ").strip()
        try:
            number = float(value)
            if number > 0:
                return number
        except ValueError:
            pass
        print("Please enter a valid positive amount.")


def add_purchase(data):
    print("\nAdd a new purchase")
    buyer = choose_person(data, "Who bought the eggs?")
    eggs = ask_positive_int("Number of eggs purchased")
    cost = ask_positive_float("Total cost for the purchase")
    entry = {
        "buyer": buyer,
        "eggs": eggs,
        "cost": cost,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    data["purchases"].append(entry)
    save_data(data)
    print("Purchase saved.\n")


def add_consumption(data):
    print("\nRecord egg consumption")
    consumer = choose_person(data, "Who consumed eggs?")
    eggs = ask_positive_int("Number of eggs consumed")
    entry = {
        "person": consumer,
        "eggs": eggs,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    data["consumptions"].append(entry)
    save_data(data)
    print("Consumption saved.\n")


def summarize(data):
    people = data["people"]
    totals = {person: {"consumed": 0, "paid": 0.0, "share": 0.0} for person in people}

    total_eggs = 0
    total_cost = 0.0
    for purchase in data["purchases"]:
        totals[purchase["buyer"]]["paid"] += purchase["cost"]
        total_eggs += purchase["eggs"]
        total_cost += purchase["cost"]

    for consumption in data["consumptions"]:
        totals[consumption["person"]]["consumed"] += consumption["eggs"]

    cost_per_egg = (total_cost / total_eggs) if total_eggs else 0.0
    for person in people:
        totals[person]["share"] = totals[person]["consumed"] * cost_per_egg

    return {
        "total_eggs": total_eggs,
        "total_cost": total_cost,
        "cost_per_egg": cost_per_egg,
        "totals": totals,
    }


def show_summary(data):
    report = summarize(data)
    print("\nEgg tracker summary")
    print(f"Total eggs purchased: {report['total_eggs']}")
    print(f"Total money spent: {report['total_cost']:.2f}")
    print(f"Cost per egg: {report['cost_per_egg']:.2f}\n")
    print(f"{'Person':<15}{'Eggs':>8}{'Paid':>12}{'Share':>12}{'Balance':>12}")
    print("-" * 59)
    for person, values in report["totals"].items():
        balance = values["paid"] - values["share"]
        print(
            f"{person:<15}{values['consumed']:>8}{values['paid']:>12.2f}{values['share']:>12.2f}{balance:>12.2f}"
        )
    print("\nBalance interpretation:")
    print("  Positive balance means the person paid more than their share.")
    print("  Negative balance means the person owes money to the group.\n")


def show_history(data):
    print("\nPurchase history")
    if not data["purchases"]:
        print("  No purchases recorded.")
    else:
        for purchase in data["purchases"]:
            print(
                f"  {purchase['date']}: {purchase['buyer']} bought {purchase['eggs']} eggs for {purchase['cost']:.2f}"
            )

    print("\nConsumption history")
    if not data["consumptions"]:
        print("  No consumption records.")
    else:
        for consumption in data["consumptions"]:
            print(
                f"  {consumption['date']}: {consumption['person']} ate {consumption['eggs']} eggs"
            )
    print()


def show_menu():
    print("Egg Tracker Menu")
    print("1. Add purchase")
    print("2. Add consumption")
    print("3. Show summary")
    print("4. Show history")
    print("5. Exit")


def main():
    data = load_data()
    ask_people(data)
    save_data(data)

    while True:
        show_menu()
        choice = input("Choose an option: ").strip()
        if choice == "1":
            add_purchase(data)
        elif choice == "2":
            add_consumption(data)
        elif choice == "3":
            show_summary(data)
        elif choice == "4":
            show_history(data)
        elif choice == "5":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please choose 1-5.\n")


if __name__ == "__main__":
    main()
