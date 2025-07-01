from flask import Flask, render_template, request
import datetime
import json
import os

app = Flask(__name__)
DATA_FILE = "data/history.json"

def save_data(data):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

def calculate_cycle(last_period_date, cycle_length, period_length):
    ovulation_day = (cycle_length - period_length) // 2
    fertile_start = ovulation_day - 5
    fertile_end = ovulation_day + 4
    next_period = last_period_date + datetime.timedelta(days=cycle_length)
    fertile_start_date = last_period_date + datetime.timedelta(days=fertile_start)
    fertile_end_date = last_period_date + datetime.timedelta(days=fertile_end)
    return {
        "ovulation_day": ovulation_day,
        "fertile_start": fertile_start_date.strftime("%Y-%m-%d"),
        "fertile_end": fertile_end_date.strftime("%Y-%m-%d"),
        "next_period": next_period.strftime("%Y-%m-%d"),
    }

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    chart_data = None
    if request.method == "POST":
        try:
            last_period_str = request.form.get("last_period_date", "").strip()
            cycle_length = request.form.get("cycle_length", "").strip()
            period_length = request.form.get("period_length", "").strip()
            symptoms = request.form.get("symptoms", "").strip()

            # Validate inputs
            if not last_period_str:
                raise ValueError("Last period date is required")
            if not cycle_length:
                raise ValueError("Cycle length is required")
            if not period_length:
                raise ValueError("Period length is required")

            # Convert and validate dates/numbers
            try:
                last_period_date = datetime.datetime.strptime(last_period_str, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("Invalid date format. Please use YYYY-MM-DD format")

            try:
                cycle_length = int(cycle_length)
                if not (20 <= cycle_length <= 45):
                    raise ValueError("Cycle length must be between 20 and 45 days")
            except ValueError:
                raise ValueError("Cycle length must be a valid number")

            try:
                period_length = int(period_length)
                if not (1 <= period_length <= 15):
                    raise ValueError("Period length must be between 1 and 15 days")
            except ValueError:
                raise ValueError("Period length must be a valid number")

            # Calculate cycle information
            cycle_info = calculate_cycle(last_period_date, cycle_length, period_length)

            entry = {
                "last_period_date": last_period_str,
                "cycle_length": cycle_length,
                "period_length": period_length,
                "symptoms": symptoms,
                **cycle_info,
                "logged_on": datetime.date.today().strftime("%Y-%m-%d"),
            }

            # Save data
            data = load_data()
            data.append(entry)
            save_data(data)

            result = entry

            # Prepare chart data from last 5 entries (or less)
            last_entries = data[-5:]
            labels = [e["last_period_date"] for e in last_entries]
            cycle_lengths = [e["cycle_length"] for e in last_entries]
            period_lengths = [e["period_length"] for e in last_entries]

            chart_data = {
                "labels": labels,
                "cycle_lengths": cycle_lengths,
                "period_lengths": period_lengths
            }

        except Exception as e:
            result = {"error": str(e)}

    return render_template("index.html", result=result, chart_data=chart_data)

if __name__ == "__main__":
    app.run(debug=True)