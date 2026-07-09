Egg Tracker
===========
A simple mobile-friendly Flask web app to track egg purchases and consumption among flatmates.

Quick start
-----------
1. Create a Python venv (recommended):

```powershell
cd d:\projects
python -m venv .venv
.\.venv\Scripts\activate
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Run the app:

```powershell
python egg_tracker_web.py
```

Open `http://127.0.0.1:5000` in your browser or, on your phone, use `http://<PC_IP>:5000` (replace `<PC_IP>` with your computer's local IP on the same wifi).

Default users
-------------
On first run the app will contain four people (change them via the `People` page). PINs are empty by default — the first time a user logs in they will be prompted to set a PIN.

How to use
----------
- Login: `Login` in the top-right. First login sets PIN for that person.
- Change your PIN: `Change PIN` after logging in.
- Add purchase: `Add purchase` — submitted purchases require approval by all flatmates before being recorded.
- Record consumption: If you record your own consumption while logged in it is recorded immediately. If you submit consumption for another person they must approve it.
- Reset data: A reset request requires approval from all flatmates. Logged-in users can approve from the dashboard.
- Force PIN reset: A logged-in user can force-all PINs to be cleared on the `People` page ("Force PIN reset for all users").

Free online hosting
-------------------
1. Put the project into a GitHub repository.
2. Sign up for a free Render account at https://render.com or Railway at https://railway.app.
3. Create a new Web Service / Project and connect your GitHub repo.
4. Use these settings:
   - Branch: your main branch
   - Build command: `pip install -r requirements.txt`
   - Start command: `python egg_tracker_web.py`
5. Deploy the app. The service will provide a public URL.
6. Open that URL in your browser and share it with your roommates.

Note: `egg_data.json` is stored on the host disk. On free tier services, disk persistence is usually fine for light use, but keep a backup of `egg_data.json` locally if you want to preserve data.

Expose to mobile (ngrok)
------------------------
Option A — local network (easiest):
- Ensure your phone is on the same Wi‑Fi as your computer.
- Find your PC IP (PowerShell):

```powershell
ipconfig
# Look for IPv4 address on your Wi-Fi adapter, e.g. 192.168.1.34
```
- Visit `http://<PC_IP>:5000` on your phone.

Option B — ngrok (tunnel) — optional
- Install ngrok from https://ngrok.com and run `ngrok http 5000`, or install `pyngrok` and use the helper below.
- The ngrok URL will forward to your local app so your phone can access it remotely.

Files added
-----------
- `egg_tracker_web.py` — main Flask app
- `templates/` — HTML templates
- `requirements.txt` — Python dependencies
- `start_ngrok.py` — optional helper (see below)

start_ngrok.py (optional helper)
--------------------------------
If you want the app accessible via a public ngrok URL and prefer a Python helper, install `pyngrok`:

```powershell
pip install pyngrok
python start_ngrok.py
```

The helper only opens a tunnel and prints the public URL. Run your Flask app separately.

Security notes
--------------
- PINs are stored hashed using Werkzeug. Do not use this app in production as-is.
- Consider HTTPS or a proper hosted solution if you need remote access for multiple users.

Questions or next steps
----------------------
If you want, I can:
- Add email notifications for approvals
- Build a small API and a mobile app wrapper
- Harden authentication (sessions, CSRF, rate limiting)
