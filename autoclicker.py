from flask import Flask, render_template, request, jsonify
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import threading, time, json, os, datetime

app = Flask(__name__)

# وضعیت اجرای اتوکلیکر
running = False
current_model = None

# مسیر لاگ
LOG_FILE = "logs.txt"

def log_message(message):
    timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp} {message}\n")
    print(f"{timestamp} {message}")

def load_cookies():
    if not os.path.exists("stripchat_login.json"):
        log_message("stripchat_login.json not found!")
        return None
    with open("stripchat_login.json", "r") as f:
        data = json.load(f)
    return data.get("cookies", [])

def automate_giveaway(model_name):
    global running
    cookies = load_cookies()
    if cookies is None:
        log_message("No cookies found, stopping automation.")
        return

    while running:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)  # headless mode
            context = browser.new_context()
            try:
                context.add_cookies(cookies)
            except Exception as e:
                log_message(f"Error loading cookies: {e}")
                browser.close()
                return

            page = context.new_page()
            try:
                url = f"https://stripchat.global/{model_name}"
                page.goto(url)
                time.sleep(60)  # 1 دقیقه صبر تا سایت کامل لود شود

                try:
                    # مرحله ۳: پیدا کردن دکمه Giveaway
                    giveaway_btn = page.query_selector("button.a11y-button.active.lottery-title-wrapper")
                    if giveaway_btn:
                        giveaway_btn.click()
                        time.sleep(3)
                        participate_btn = page.query_selector("button.btn.btn-auth-banner.btn-inline-block")
                        if participate_btn:
                            participate_btn.click()
                            time.sleep(3)
                            # بررسی موفقیت
                            if "You have entered the token giveaway!" in page.content():
                                log_message(f"Clicked successfully for {model_name}")
                            else:
                                log_message(f"Failed to enter giveaway for {model_name}")
                        else:
                            log_message("Participate button not found")
                    else:
                        log_message("Giveaway button not found")
                except PlaywrightTimeout:
                    log_message("Timeout during automation")
                except Exception as e:
                    log_message(f"Error: {e}")
            finally:
                browser.close()
                log_message("Browser closed for this cycle")

        # تکرار هر ۳۰ دقیقه
        for _ in range(1800):
            if not running:
                break
            time.sleep(1)

    log_message("Automation stopped completely")

@app.route("/")
def index():
    return render_template("autoclicker.html")

@app.route("/start", methods=["POST"])
def start():
    global running, current_model
    model = request.json.get("model")
    if not model:
        return jsonify({"status": "error", "message": "Model name required"})
    if running:
        return jsonify({"status": "error", "message": "Automation already running"})
    running = True
    current_model = model
    thread = threading.Thread(target=automate_giveaway, args=(model,))
    thread.start()
    return jsonify({"status": "success", "message": f"Started automation for {model}"})

@app.route("/stop", methods=["POST"])
def stop():
    global running
    running = False
    return jsonify({"status": "success", "message": "Automation stopped"})

@app.route("/logs", methods=["GET"])
def get_logs():
    if not os.path.exists(LOG_FILE):
        return jsonify([])
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
    return jsonify(lines[-50:])  # آخرین ۵۰ خط

if __name__ == "__main__":
    app.run(debug=True)
