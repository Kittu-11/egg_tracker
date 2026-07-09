import json
import os
from datetime import datetime
from functools import wraps
from io import BytesIO

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    g,
    send_file,
)
from werkzeug.security import generate_password_hash, check_password_hash

DATA_FILE = "egg_data.json"
DEFAULT_PEOPLE = ["Person 1", "Person 2", "Person 3", "Person 4"]

app = Flask(__name__)
app.secret_key = "replace-with-a-secure-random-key"


def load_data():
    if not os.path.exists(DATA_FILE):
        # default structure includes users, pending lists and reset votes
        users = {name: None for name in DEFAULT_PEOPLE}
        return {
            "people": DEFAULT_PEOPLE,
            "users": users,
            "purchases": [],
            "consumptions": [],
            "pending_purchases": [],
            "pending_consumptions": [],
            "pending_deletions": [],
            "admins": [],
            "reset_votes": [],
        }

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)
        # ensure new keys exist for older files
        data.setdefault("users", {name: None for name in data.get("people", DEFAULT_PEOPLE)})
        # migrate any plaintext PINs to hashed form where possible
        migrated = False
        users = data.get("users", {})
        known_hash_prefixes = ("pbkdf2:", "scrypt:", "argon2:", "bcrypt:")
        for name, pin in list(users.items()):
            if pin is None:
                continue
            if isinstance(pin, str) and pin.startswith(known_hash_prefixes):
                continue
            # otherwise assume plaintext and hash it
            users[name] = generate_password_hash(str(pin))
            migrated = True
        if migrated:
            data["users"] = users
            save_data(data)
        data.setdefault("pending_purchases", [])
        data.setdefault("pending_consumptions", [])
        data.setdefault("pending_deletions", [])
        data.setdefault("admins", [])
        data.setdefault("reset_votes", [])
        return data


def save_data(data):
    try:
        # create backup before saving
        if os.path.exists(DATA_FILE):
            backup_file = DATA_FILE.replace(".json", ".backup.json")
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                backup_data = f.read()
            with open(backup_file, "w", encoding="utf-8") as f:
                f.write(backup_data)
        # save new data
        with open(DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
    except Exception as e:
        print(f"Error saving data: {e}")
        raise


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            flash("Please login to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return wrapped


@app.before_request
def load_current_user():
    g.user = session.get("user")


def summarize(data):
    people = data.get("people", DEFAULT_PEOPLE)
    totals = {person: {"consumed": 0, "paid": 0.0, "share": 0.0} for person in people}

    total_eggs = 0
    total_cost = 0.0
    for purchase in data.get("purchases", []):
        buyer = purchase.get("buyer")
        totals[buyer]["paid"] += purchase.get("cost", 0.0)
        total_eggs += purchase.get("eggs", 0)
        total_cost += purchase.get("cost", 0.0)

    for consumption in data.get("consumptions", []):
        person = consumption.get("person")
        totals[person]["consumed"] += consumption.get("eggs", 0)

    cost_per_egg = total_cost / total_eggs if total_eggs else 0.0
    for person in people:
        totals[person]["share"] = totals[person]["consumed"] * cost_per_egg

    return {
        "people": people,
        "total_eggs": total_eggs,
        "total_cost": total_cost,
        "cost_per_egg": cost_per_egg,
        "totals": totals,
    }


def clean_people(raw_names):
    names = [name.strip() for name in raw_names.split(",") if name.strip()]
    return names if len(names) == 4 else None


def add_purchase_record(data, buyer, eggs, cost, date_text):
    if date_text:
        date_text = date_text.replace("T", " ")
    entry = {
        "buyer": buyer,
        "eggs": eggs,
        "cost": cost,
        "date": date_text or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    data["purchases"].append(entry)
    save_data(data)


def add_consumption_record(data, person, eggs):
    entry = {
        "person": person,
        "eggs": eggs,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    data["consumptions"].append(entry)
    save_data(data)


def add_pending_purchase(data, buyer, eggs, cost, date_text, submitter):
    if date_text:
        date_text = date_text.replace("T", " ")
    entry = {
        "buyer": buyer,
        "eggs": eggs,
        "cost": cost,
        "date": date_text or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "approvals": [],
        "declines": [],
        "status": "pending",
        "submitter": submitter,
    }
    data.setdefault("pending_purchases", []).append(entry)
    save_data(data)


def add_pending_consumption(data, person, eggs, submitter):
    entry = {
        "person": person,
        "eggs": eggs,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "approvals": [],
        "submitter": submitter,
    }
    data.setdefault("pending_consumptions", []).append(entry)
    save_data(data)


def add_pending_deletion(data, consumption_item, requester):
    entry = {
        "person": consumption_item.get("person"),
        "eggs": consumption_item.get("eggs"),
        "date": consumption_item.get("date"),
        "requester": requester,
        "approvals": [],
    }
    data.setdefault("pending_deletions", []).append(entry)
    save_data(data)


@app.route("/")
def index():
    data = load_data()
    report = summarize(data)
    recent_consumptions = list(reversed(data.get("consumptions", [])))[:5]
    recent_purchases = list(reversed(data.get("purchases", [])))[:5]
    reset_votes = data.get("reset_votes", [])
    pending = [p for p in data.get("people", []) if p not in reset_votes]
    pending_purchases = data.get("pending_purchases", [])
    pending_consumptions = data.get("pending_consumptions", [])
    pending_deletions = data.get("pending_deletions", [])
    return render_template(
        "index.html",
        data=data,
        report=report,
        recent_consumptions=recent_consumptions,
        recent_purchases=recent_purchases,
        reset_votes=reset_votes,
        pending=pending,
        pending_purchases=pending_purchases,
        pending_consumptions=pending_consumptions,
        pending_deletions=pending_deletions,
    )


@app.route("/people", methods=["GET", "POST"])
def people():
    data = load_data()
    if request.method == "POST":
        raw_names = request.form.get("people", "")
        names = clean_people(raw_names)
        if names:
            # preserve existing pins where possible; new entries start with no PIN
            old_users = data.get("users", {})
            new_users = {name: old_users.get(name) for name in names}
            data["people"] = names
            data["users"] = new_users
            save_data(data)
            flash("People updated successfully.", "success")
            return redirect(url_for("index"))
        flash("Please enter exactly 4 names separated by commas.", "danger")

    return render_template("people.html", data=data)


@app.route("/login", methods=["GET", "POST"])
def login():
    data = load_data()
    if request.method == "POST":
        person = request.form.get("person")
        pin = request.form.get("pin")
        users = data.get("users", {})
        if not person:
            flash("Select a person.", "danger")
            return redirect(url_for("login"))

        stored = users.get(person)
        # first-time set PIN: if stored is None, handle default or provided PIN
        if stored is None:
            # allow a default starter PIN of '0000' — save it and force immediate change
            if pin == "0000":
                users[person] = generate_password_hash("0000")
                data["users"] = users
                save_data(data)
                session["user"] = person
                flash("Default PIN used — please change your PIN now.", "warning")
                return redirect(url_for("change_pin"))
            # otherwise accept the provided PIN as first-time set
            users[person] = generate_password_hash(pin)
            data["users"] = users
            save_data(data)
            session["user"] = person
            flash("PIN set and logged in.", "success")
            return redirect(url_for("index"))

        # otherwise validate
        try:
            if check_password_hash(stored, pin):
                session["user"] = person
                flash(f"Logged in as {person}.", "success")
                return redirect(url_for("index"))
        except Exception:
            # any error treat as invalid
            pass
        flash("Invalid name or PIN.", "danger")

    return render_template("login.html", data=data)


@app.route("/reset_pin", methods=["POST"])
def reset_pin():
    data = load_data()
    person = request.form.get("person")
    current = request.form.get("current_pin")
    new = request.form.get("new_pin")
    confirm = request.form.get("confirm_pin")

    if not person or not current or not new:
        flash("Please provide person, current PIN and new PIN.", "danger")
        return redirect(url_for("login"))

    if new != confirm:
        flash("New PINs do not match.", "danger")
        return redirect(url_for("login"))

    users = data.get("users", {})
    stored = users.get(person)
    if stored is None:
        flash("No existing PIN for this user — use first-time login to set a PIN.", "danger")
        return redirect(url_for("login"))

    try:
        if check_password_hash(stored, current):
            users[person] = generate_password_hash(new)
            data["users"] = users
            save_data(data)
            # optionally log the user in after reset
            session["user"] = person
            flash("PIN updated successfully and logged in.", "success")
            return redirect(url_for("index"))
    except Exception:
        pass

    flash("Current PIN is incorrect.", "danger")
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out.", "info")
    return redirect(url_for("index"))


@app.route("/change_pin", methods=["GET", "POST"])
@login_required
def change_pin():
    data = load_data()
    if request.method == "POST":
        current = request.form.get("current", "")
        new = request.form.get("new", "")
        confirm = request.form.get("confirm", "")
        users = data.get("users", {})
        user = g.user
        stored = users.get(user)
        if stored is None or not check_password_hash(stored, current):
            flash("Current PIN is incorrect.", "danger")
            return redirect(url_for("change_pin"))
        if not new or new != confirm:
            flash("New PINs do not match.", "danger")
            return redirect(url_for("change_pin"))
        users[user] = generate_password_hash(new)
        data["users"] = users
        save_data(data)
        flash("PIN updated successfully.", "success")
        return redirect(url_for("index"))
    return render_template("change_pin.html", data=data)


@app.route("/purchase", methods=["GET", "POST"])
@login_required
def purchase():
    data = load_data()
    if request.method == "POST":
        buyer = request.form.get("buyer")
        eggs = request.form.get("eggs")
        cost = request.form.get("cost")
        date_text = request.form.get("date")

        if not buyer or not eggs or not cost:
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for("purchase"))

        try:
            eggs_value = int(eggs)
            cost_value = float(cost)
            if eggs_value <= 0 or cost_value <= 0:
                raise ValueError
        except ValueError:
            flash("Egg count and cost must be positive numbers.", "danger")
            return redirect(url_for("purchase"))

        # create pending purchase which requires approvals from all people
        submitter = g.user or "(unknown)"
        add_pending_purchase(data, buyer, eggs_value, cost_value, date_text, submitter)
        flash("Purchase submitted for approval by all roommates.", "warning")
        return redirect(url_for("index"))

    return render_template("purchase.html", data=data)


@app.route("/purchase/approve/<int:idx>", methods=["POST"])
@login_required
def purchase_approve(idx):
    data = load_data()
    pending = data.get("pending_purchases", [])
    if idx < 0 or idx >= len(pending):
        flash("Invalid pending purchase.", "danger")
        return redirect(url_for("index"))
    item = pending[idx]
    user = g.user
    if item.get("status") != "pending":
        flash(f"This purchase has already been {item.get('status')}.", "info")
        return redirect(url_for("index"))
    if user in item.get("approvals", []) or user in item.get("declines", []):
        flash("You have already responded to this purchase.", "info")
        return redirect(url_for("index"))
    item.setdefault("approvals", []).append(user)
    people_count = len(data.get("people", []))
    if len(item["approvals"]) >= people_count:
        item["status"] = "approved"
        data.setdefault("purchases", []).append({k: item[k] for k in ("buyer", "eggs", "cost", "date")})
        pending.pop(idx)
        flash("Purchase approved by all and recorded.", "success")
    else:
        flash(f"{user} approved the purchase. Waiting for others.", "warning")
    save_data(data)
    return redirect(url_for("index"))


@app.route("/purchase/reject/<int:idx>", methods=["POST"])
@login_required
def purchase_reject(idx):
    data = load_data()
    pending = data.get("pending_purchases", [])
    if idx < 0 or idx >= len(pending):
        flash("Invalid pending purchase.", "danger")
        return redirect(url_for("index"))
    item = pending[idx]
    user = g.user
    if item.get("status") != "pending":
        flash(f"This purchase has already been {item.get('status')}.", "info")
        return redirect(url_for("index"))
    if user in item.get("approvals", []) or user in item.get("declines", []):
        flash("You have already responded to this purchase.", "info")
        return redirect(url_for("index"))
    item.setdefault("declines", []).append(user)
    item["status"] = "rejected"
    save_data(data)
    flash("Purchase declined and marked rejected.", "info")
    return redirect(url_for("index"))


@app.route("/consume", methods=["POST"])
@login_required
def consume():
    data = load_data()
    person = request.form.get("person")
    eggs = request.form.get("eggs")
    if not person or not eggs:
        flash("Select a person and enter the number of eggs.", "danger")
        return redirect(url_for("index"))

    try:
        eggs_value = int(eggs)
        if eggs_value <= 0:
            raise ValueError
    except ValueError:
        flash("Egg count must be a positive whole number.", "danger")
        return redirect(url_for("index"))

    user = g.user
    if user and user == person:
        # self-recording: immediate
        add_consumption_record(data, person, eggs_value)
        flash("Consumption recorded.", "success")
    else:
        submitter = user or "(unknown)"
        add_pending_consumption(data, person, eggs_value, submitter)
        flash("Consumption submitted for approval by the person.", "warning")
    return redirect(url_for("index"))


@app.route("/consume/approve/<int:idx>", methods=["POST"])
@login_required
def consume_approve(idx):
    data = load_data()
    pending = data.get("pending_consumptions", [])
    if idx < 0 or idx >= len(pending):
        flash("Invalid pending consumption.", "danger")
        return redirect(url_for("index"))
    item = pending[idx]
    user = g.user
    # only the person who is the target can approve
    if user != item.get("person"):
        flash("Only the person who consumed can approve this record.", "danger")
        return redirect(url_for("index"))
    # mark as approved and move to confirmed consumptions
    item["status"] = "approved"
    confirmed_entry = {k: item[k] for k in ("person", "eggs", "date")}
    data.setdefault("consumptions", []).append(confirmed_entry)
    save_data(data)
    flash("Consumption approved and recorded.", "success")
    return redirect(url_for("index"))


@app.route('/consume/reject/<int:idx>', methods=['POST'])
@login_required
def consume_reject(idx):
    data = load_data()
    pending = data.get("pending_consumptions", [])
    if idx < 0 or idx >= len(pending):
        flash("Invalid pending consumption.", "danger")
        return redirect(url_for("index"))
    item = pending[idx]
    user = g.user
    if user != item.get("person"):
        flash("Only the person who consumed can reject this record.", "danger")
        return redirect(url_for("index"))
    # mark as rejected and remove from pending
    item["status"] = "rejected"
    pending[idx] = item
    data["pending_consumptions"] = pending
    save_data(data)
    flash("Pending consumption rejected.", "info")
    return redirect(url_for("index"))


@app.route('/consumption/delete/<int:idx>', methods=['POST'])
@login_required
def delete_consumption(idx):
    data = load_data()
    consumptions = data.get('consumptions', [])
    if idx < 0 or idx >= len(consumptions):
        flash('Invalid consumption entry.', 'danger')
        return redirect(url_for('index'))
    item = consumptions[idx]
    user = g.user
    # only the person who consumed can delete immediately
    if user == item.get('person'):
        consumptions.pop(idx)
        data['consumptions'] = consumptions
        save_data(data)
        flash('Consumption entry deleted.', 'success')
        return redirect(url_for('index'))

    # otherwise create a pending deletion request requiring the person's approval
    add_pending_deletion(data, item, user)
    flash('Deletion requested. Awaiting approval from the person who consumed.', 'warning')
    return redirect(url_for('index'))


@app.route('/consumption/delete/approve/<int:pending_idx>', methods=['POST'])
@login_required
def approve_consumption_deletion(pending_idx):
    data = load_data()
    pending = data.get('pending_deletions', [])
    if pending_idx < 0 or pending_idx >= len(pending):
        flash('Invalid pending deletion.', 'danger')
        return redirect(url_for('index'))
    item = pending[pending_idx]
    user = g.user
    # only the person who consumed can approve deletion
    if user != item.get('person'):
        flash('Only the person who consumed can approve deletion.', 'danger')
        return redirect(url_for('index'))

    # find matching consumption entry by person/date/eggs and remove first match
    consumptions = data.get('consumptions', [])
    match_idx = None
    for i, c in enumerate(consumptions):
        if c.get('person') == item.get('person') and c.get('date') == item.get('date') and c.get('eggs') == item.get('eggs'):
            match_idx = i
            break

    if match_idx is not None:
        consumptions.pop(match_idx)
        data['consumptions'] = consumptions
        flash('Consumption entry deleted after approval.', 'success')
    else:
        flash('Matching consumption record not found; it may have been removed already.', 'info')

    # remove pending request
    pending.pop(pending_idx)
    data['pending_deletions'] = pending
    save_data(data)
    return redirect(url_for('index'))


@app.route("/history")
def history():
    data = load_data()
    report = summarize(data)
    return render_template("history.html", data=data, report=report)


@app.route("/reset/vote", methods=["POST"])
@login_required
def reset_vote():
    data = load_data()
    person = g.user

    if not person or person not in data.get("people", []):
        flash("Invalid person selected.", "danger")
        return redirect(url_for("index"))

    reset_votes = data.get("reset_votes", [])
    if person in reset_votes:
        flash(f"{person} has already voted to reset.", "info")
        return redirect(url_for("index"))

    reset_votes.append(person)
    data["reset_votes"] = reset_votes
    people_count = len(data.get("people", []))

    if len(reset_votes) == people_count:
        data["purchases"] = []
        data["consumptions"] = []
        data["reset_votes"] = []
        flash("Data reset! All records cleared.", "success")
    else:
        votes_needed = people_count - len(reset_votes)
        flash(f"{person} voted to reset. {votes_needed} more vote(s) needed.", "warning")

    save_data(data)
    return redirect(url_for("index"))

@app.route("/reset/cancel", methods=["POST"])
@login_required
def reset_cancel():
    data = load_data()
    data["reset_votes"] = []
    save_data(data)
    flash("Reset request cancelled.", "info")
    return redirect(url_for("index"))


@app.route("/force_pin_reset", methods=["POST"])
@login_required
def force_pin_reset():
    """Invalidate all stored PINs so each user must set a new PIN on next login."""
    data = load_data()
    users = data.get("users", {})
    for name in list(users.keys()):
        users[name] = None
    data["users"] = users
    save_data(data)
    flash("All users will be required to set new PINs on next login.", "success")
    return redirect(url_for("people"))


@app.route("/download_data")
@login_required
def download_data():
    """Download egg_data.json for backup."""
    data = load_data()
    json_str = json.dumps(data, indent=2)
    bytes_io = BytesIO(json_str.encode('utf-8'))
    return send_file(
        bytes_io,
        mimetype='application/json',
        as_attachment=True,
        download_name=f'egg_data_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
