from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = "supersegretodasalvatore"

BASE = os.path.dirname(os.path.abspath(__file__))
UTENTI_FILE = os.path.join(BASE, "utenti.csv")
TURNI_FILE = os.path.join(BASE, "turni.csv")
MEZZI_FILE = os.path.join(BASE, "mezzi.csv")

def carica_utenti():
    return pd.read_csv(UTENTI_FILE, sep=";")

def carica_turni():
    df = pd.read_csv(TURNI_FILE, sep=";")
    df["data"] = pd.to_datetime(df["data"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["data"])
    df["data"] = df["data"].dt.strftime("%d/%m/%Y")
    return df

def carica_mezzi():
    df = pd.read_csv(MEZZI_FILE, sep=";")
    df["data"] = pd.to_datetime(df["data"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["data"])
    df["data"] = df["data"].dt.strftime("%d/%m/%Y")
    return df# ================================
# Login e logout
# ================================
@app.route("/", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        utenti = carica_utenti()
        match = utenti[(utenti["username"] == username) & (utenti["password"] == password)]
        if not match.empty:
            session["username"] = username
            session["ruolo"] = match.iloc[0]["ruolo"]
            return redirect(url_for("dashboard"))
        error = "Credenziali errate."
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ================================
# Dashboard utente
# ================================
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))

    oggi = datetime.today().date()
    if request.method == "POST" and request.form.get("data"):
        oggi = datetime.strptime(request.form["data"], "%Y-%m-%d").date()

    df_turni = pd.read_csv(TURNI_FILE, sep=";")
    df_turni["data"] = pd.to_datetime(df_turni["data"], dayfirst=True, errors="coerce")
    user = session["username"]
    turni = df_turni[(df_turni["username"] == user) & (df_turni["data"].dt.date == oggi)]
    squadra = turni.iloc[0]["squadra"] if not turni.empty else None

    df_mezzi = pd.read_csv(MEZZI_FILE, sep=";")
    df_mezzi["data"] = pd.to_datetime(df_mezzi["data"], dayfirst=True, errors="coerce")
    mezzi = df_mezzi[(df_mezzi["squadra"] == squadra) & (df_mezzi["data"].dt.date == oggi)] if squadra else pd.DataFrame()

    return render_template("dashboard.html", username=user, data=oggi,
                           turni=turni.to_dict("records"),
                           mezzi=mezzi.to_dict("records"))

# ================================
# Admin settimanale
# ================================
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if session.get("ruolo") != "admin":
        return redirect(url_for("dashboard"))

    oggi = datetime.today().date()
    if request.method == "POST" and request.form.get("data"):
        oggi = datetime.strptime(request.form["data"], "%Y-%m-%d").date()

    lunedi = oggi - timedelta(days=oggi.weekday())
    settimana = [lunedi + timedelta(days=i) for i in range(7)]

    df_turni = carica_turni()
    df_mezzi = carica_mezzi()

    turni = [
        t for t in df_turni.to_dict("records")
        if isinstance(t["data"], str) and datetime.strptime(t["data"], "%d/%m/%Y").date() in settimana
    ]
    mezzi = [
        m for m in df_mezzi.to_dict("records")
        if isinstance(m["data"], str) and datetime.strptime(m["data"], "%d/%m/%Y").date() in settimana
    ]

    return render_template("admin_settimanale.html",
                           giorni=settimana,
                           turni=turni,
                           mezzi=mezzi,
                           data_riferimento=oggi)# ================================
 @app.route("/inserisci-turno", methods=["GET", "POST"])
def inserisci_turno():
    if session.get("ruolo") != "admin":
        return redirect(url_for("dashboard"))

    utenti = carica_utenti()["username"].tolist()
    data_default = datetime.today().strftime("%Y-%m-%d")

    if request.method == "POST":
        data = request.form["data"]
        username = request.form["username"]
        squadra = request.form["squadra"]

        df = pd.read_csv(TURNI_FILE, sep=";")
        nuovo_turno = {
            "data": pd.to_datetime(data, dayfirst=False, errors="coerce"),
            "username": username,
            "squadra": squadra,
            "turno": "Mattina"  # oppure un campo libero nel form
        }
        df = pd.concat([df, pd.DataFrame([nuovo_turno])], ignore_index=True)
        df["data"] = pd.to_datetime(df["data"], dayfirst=True, errors="coerce")
        df["data"] = df["data"].dt.strftime("%d/%m/%Y")
        df.to_csv(TURNI_FILE, sep=";", index=False)

        return redirect(url_for("admin"))

    return render_template("inserisci_turno.html", utenti=utenti, data_default=data_default)
# Gestione mezzi
# ================================
@app.route("/admin/mezzi", methods=["GET", "POST"])
def gestione_mezzi():
    if session.get("ruolo") != "admin":
        return redirect(url_for("dashboard"))

    df = carica_mezzi()

    if request.method == "POST":
        if request.form["action"] == "aggiungi":
            nuovo = {
                "squadra": request.form["squadra"],
                "mezzo": request.form["mezzo"],
                "targa": request.form["targa"],
                "note": request.form["note"],
                "data": pd.to_datetime(request.form["data"], dayfirst=True, errors="coerce")
            }
            df = pd.concat([df, pd.DataFrame([nuovo])], ignore_index=True)
        elif request.form["action"] == "cancella":
            idx = int(request.form["indice"])
            df = df.drop(idx).reset_index(drop=True)

        df["data"] = pd.to_datetime(df["data"], dayfirst=True, errors="coerce")
        df["data"] = df["data"].dt.strftime("%d/%m/%Y")
        df.to_csv(MEZZI_FILE, sep=";", index=False)
        return redirect(url_for("gestione_mezzi"))

    return render_template("gestione_mezzi.html", mezzi=df.reset_index())

# ================================
# Avvio server Flask
# ================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=True)