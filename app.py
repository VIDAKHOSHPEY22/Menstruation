from flask import Flask, render_template, request
import datetime
import jdatetime
import json
import os
from persiantools.jdatetime import JalaliDate, JalaliDateTime

app = Flask(__name__)
DATA_FILE = "data/history.json"

def save_data(data):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    return []

def jalali_to_gregorian(jalali_date_str):
    """تبدیل تاریخ شمسی به میلادی"""
    year, month, day = map(int, jalali_date_str.split('/'))
    jalali_date = JalaliDate(year, month, day)
    return jalali_date.to_gregorian()

def gregorian_to_jalali(date_obj):
    """تبدیل تاریخ میلادی به شمسی"""
    if isinstance(date_obj, str):
        date_obj = datetime.datetime.strptime(date_obj, "%Y-%m-%d").date()
    jalali_date = JalaliDate(date_obj)
    return jalali_date.strftime("%Y/%m/%d")

def calculate_cycle(last_period_date, cycle_length, period_length):
    ovulation_day = (cycle_length - period_length) // 2
    fertile_start = max(ovulation_day - 5, 1)
    fertile_end = ovulation_day + 4
    next_period = last_period_date + datetime.timedelta(days=cycle_length)
    fertile_start_date = last_period_date + datetime.timedelta(days=fertile_start)
    fertile_end_date = last_period_date + datetime.timedelta(days=fertile_end)
    
    return {
        "ovulation_day": ovulation_day,
        "fertile_start": fertile_start_date,
        "fertile_end": fertile_end_date,
        "next_period": next_period,
    }

def get_jalali_weekday(date_obj):
    """گرفتن نام روز هفته به فارسی"""
    weekdays = {
        0: "شنبه",
        1: "یکشنبه",
        2: "دوشنبه",
        3: "سه‌شنبه",
        4: "چهارشنبه",
        5: "پنجشنبه",
        6: "جمعه"
    }
    if isinstance(date_obj, str):
        date_obj = datetime.datetime.strptime(date_obj, "%Y-%m-%d").date()
    jalali_date = JalaliDate(date_obj)
    return weekdays[jalali_date.weekday()]

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    chart_data = None
    today_jalali = gregorian_to_jalali(datetime.date.today())
    today_weekday = get_jalali_weekday(datetime.date.today())
    
    if request.method == "POST":
        try:
            last_period_jalali = request.form.get("last_period_date", "").strip()
            cycle_length_str = request.form.get("cycle_length", "").strip()
            period_length_str = request.form.get("period_length", "").strip()
            symptoms = request.form.get("symptoms", "").strip()
            period_status = request.form.get("period_status", "").strip()

            # اعتبارسنجی ورودی‌ها
            if not last_period_jalali:
                raise ValueError("تاریخ آخرین پریود الزامی است")
            if not cycle_length_str:
                raise ValueError("طول سیکل الزامی است")
            if not period_length_str:
                raise ValueError("مدت پریود الزامی است")

            # تبدیل تاریخ شمسی به میلادی
            try:
                last_period_date = jalali_to_gregorian(last_period_jalali)
            except Exception as e:
                raise ValueError("فرمت تاریخ نامعتبر است. لطفاً تاریخ را به صورت شمسی وارد کنید (مثال: 1403/05/15)")

            # تبدیل و اعتبارسنجی اعداد
            try:
                cycle_length = int(cycle_length_str)
            except ValueError:
                raise ValueError("طول سیکل باید یک عدد صحیح باشد")
            
            try:
                period_length = int(period_length_str)
            except ValueError:
                raise ValueError("مدت پریود باید یک عدد صحیح باشد")
            
            if not (20 <= cycle_length <= 45):
                raise ValueError("طول سیکل باید بین 20 تا 45 روز باشد")
            if not (1 <= period_length <= 15):
                raise ValueError("مدت پریود باید بین 1 تا 15 روز باشد")

            # محاسبات سیکل
            cycle_info = calculate_cycle(last_period_date, cycle_length, period_length)

            # ایجاد نتیجه با نام‌گذاری صحیح کلیدها
            result = {
                "last_period_date": last_period_date.strftime("%Y-%m-%d"),  # میلادی برای ذخیره
                "last_period": last_period_jalali,  # شمسی برای نمایش
                "last_period_weekday": get_jalali_weekday(last_period_date),
                "next_period": gregorian_to_jalali(cycle_info["next_period"]),
                "next_period_weekday": get_jalali_weekday(cycle_info["next_period"]),
                "fertile_start": gregorian_to_jalali(cycle_info["fertile_start"]),
                "fertile_start_weekday": get_jalali_weekday(cycle_info["fertile_start"]),
                "fertile_end": gregorian_to_jalali(cycle_info["fertile_end"]),
                "fertile_end_weekday": get_jalali_weekday(cycle_info["fertile_end"]),
                "cycle_length": cycle_length,
                "period_length": period_length,
                "symptoms": symptoms,
                "period_status": period_status,
                "ovulation_day": cycle_info["ovulation_day"],
                "logged_on": today_jalali,
                "logged_on_weekday": today_weekday
            }

            # ذخیره داده‌ها
            data = load_data()
            data.append({
                "last_period_date": last_period_date.strftime("%Y-%m-%d"),
                "cycle_length": cycle_length,
                "period_length": period_length,
                "symptoms": symptoms,
                "fertile_start": cycle_info["fertile_start"].strftime("%Y-%m-%d"),
                "fertile_end": cycle_info["fertile_end"].strftime("%Y-%m-%d"),
                "next_period": cycle_info["next_period"].strftime("%Y-%m-%d"),
                "logged_on": datetime.date.today().strftime("%Y-%m-%d")
            })
            save_data(data)

            # آماده‌سازی داده‌های نمودار
            last_entries = data[-5:]
            chart_data = {
                "labels": [gregorian_to_jalali(e["last_period_date"]) for e in last_entries],
                "cycle_lengths": [e["cycle_length"] for e in last_entries],
                "period_lengths": [e["period_length"] for e in last_entries]
            }

        except Exception as e:
            result = {"error": str(e)}

    return render_template("index.html", 
                         result=result, 
                         chart_data=chart_data,
                         today_jalali=today_jalali,
                         today_weekday=today_weekday)

if __name__ == "__main__":
    app.run(debug=True)