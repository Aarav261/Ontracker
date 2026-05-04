# OnTrack Morning Brief

A CLI tool that generates a daily prioritised task summary from your [OnTrack](https://github.com/doubtfire-lms/doubtfire-web) units and delivers it as a formatted HTML email — or opens it in your browser.

## What it does

Every weekday morning it fetches your active OnTrack projects, scores each task by urgency and grade target, and emails you a brief broken into sections:

| Section | Tasks included |
|---|---|
| 🚨 Needs Attention | Overdue, redo, fix & resubmit, need help |
| 🎯 Upcoming Tasks | Not started, in progress |
| 💬 Discuss with Tutor | Discuss, demonstrate |
| 📬 Submitted | Waiting on tutor feedback |
| ✅ Recently Completed | Finished within the last N days |

Urgent tasks with pending tutor feedback show the latest tutor comment inline.

## Project structure

```
brief.py           # CLI entry point
builder.py         # Priority scoring and brief assembly
constants.py       # Grade/status lookup tables
fetcher.py         # OnTrack CLI calls and API auth
mailer.py          # SMTP email delivery
renderer.py        # HTML rendering
scheduler.py       # Cron job installation
config.ini         # Your credentials (never committed — see .gitignore)
config.ini.template
```

## Requirements

- Python 3.10+
- [`ontrack-cli`](https://github.com/doubtfire-lms/ontrack-cli) installed and authenticated (`ontrack login`)
- A Gmail account with [App Passwords](https://myaccount.google.com/apppasswords) enabled (for email delivery)
- `requests` library: `pip install requests`

## Setup

**1. Clone and install dependencies**

```bash
git clone https://github.com/yourusername/ontrack-morning-brief.git
cd ontrack-morning-brief
pip install requests
```

**2. Configure**

```bash
cp config.ini.template config.ini
```

Edit `config.ini` with your Gmail address and App Password.

**3. Authenticate OnTrack**

```bash
ontrack login
```

**4. Test it**

```bash
python brief.py --preview
```

This opens the brief in your browser without sending any email.

## Usage

```
# Open brief in browser (no email)
python brief.py --preview

# Send brief via email
python brief.py

# Install weekday cron job at 8:00 AM
python brief.py --schedule

# Install at a custom hour (e.g. 7:30 AM)
python brief.py --schedule --hour 7
```

## Scheduling

The `--schedule` flag installs a cron entry that runs the brief on weekdays at the specified hour. Logs are written to `brief.log` in the project directory.

To remove the scheduled job:

```bash
crontab -e   # delete the line containing "ontrack-morning-brief"
```

## Configuration reference

`config.ini` supports these keys:

```ini
[email]
sender     = you@gmail.com
recipient  = you@gmail.com
app_password = xxxx xxxx xxxx xxxx

[brief]
recently_completed_days = 7   # days to show in "Recently Completed"
max_todo_tasks = 10           # cap on "Upcoming Tasks" rows
```
