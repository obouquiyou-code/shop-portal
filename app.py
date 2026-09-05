from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.secret_key = "dev-secret-key"

def login_required():
    if "user_id" not in session:
        return False
    return True

def init_db():
    conn = sqlite3.connect("shops.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_name TEXT NOT NULL,
            niche TEXT NOT NULL,
            sub_niche TEXT,
            domain TEXT,
            shopify_url TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shop_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shop_id) REFERENCES shops(id)
        )
    """)

    conn.commit()
    conn.close()

def migrate_db():
    conn = sqlite3.connect("shops.db")
    cursor = conn.cursor()

    columns = {
    "status": "TEXT DEFAULT 'Nouvelle demande'",
    "payment_status": "TEXT DEFAULT 'En attente'",
    "logo_status": "TEXT DEFAULT 'En attente'",
    "logo_url": "TEXT",
    "created_at": "TEXT",
    "client_name": "TEXT",
    "client_email": "TEXT",
    "gender": "TEXT",
    "phone": "TEXT",
    "shop_language": "TEXT",
    "product_count": "INTEGER",
    "issue_domain": "INTEGER DEFAULT 0",
    "issue_shopify_access": "INTEGER DEFAULT 0",
    "issue_products": "INTEGER DEFAULT 0",
    "issue_theme": "INTEGER DEFAULT 0",
    "issue_other": "INTEGER DEFAULT 0",
    "issue_comment": "TEXT",
    "request_status": "TEXT DEFAULT 'Nouvelle demande'",
    "config_status": "TEXT DEFAULT 'À faire'",
    "final_status": "TEXT DEFAULT 'En attente'"

    }

    conn = sqlite3.connect("shops.db")
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(shop_history)")
    history_columns = [column[1] for column in cursor.fetchall()]

    if "role" not in history_columns:
        cursor.execute("""
            ALTER TABLE shop_history
            ADD COLUMN role TEXT
        """)


    cursor.execute("PRAGMA table_info(shops)")
    existing_columns = [column[1] for column in cursor.fetchall()]

    for column_name, column_type in columns.items():
        if column_name not in existing_columns:
            cursor.execute(
                f"ALTER TABLE shops ADD COLUMN {column_name} {column_type}"
            )

    cursor.execute("""
        UPDATE shops
        SET created_at = datetime('now')
        WHERE created_at IS NULL
    """)

    conn.commit()
    conn.close()

def init_users():
    conn = sqlite3.connect("shops.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    users = [
        ("admin", "admin123", "super_admin"),
        ("lise", "lise123", "payment"),
        ("designer", "designer123", "designer"),
        ("sav", "sav123", "reader"),
        ("config", "config123", "shop_config")
    ]

    for username, password, role in users:
        cursor.execute("""
            INSERT OR IGNORE INTO users (
                username,
                password,
                role
            )
            VALUES (?, ?, ?)
        """, (
            username,
            password,
            role
        ))

    conn.commit()
    conn.close()

def get_azure_sql_connection():
    connection_string = os.getenv("AZURE_SQL_CONNECTION_STRING")

    if not connection_string:
        raise RuntimeError("AZURE_SQL_CONNECTION_STRING est introuvable.")

    return pyodbc.connect(connection_string)

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/create-shop", methods=["POST"])
def create_shop():
    client_name = request.form["client_name"]
    client_email = request.form["client_email"]
    shop_name = request.form["shop_name"]
    niche = request.form["niche"]
    sub_niche = request.form["sub_niche"]
    domain = request.form["domain"]
    shopify_url = request.form["shopify_url"]
    gender = request.form["gender"]
    phone = request.form["phone"]
    shop_language = request.form["shop_language"]
    product_count = request.form["product_count"]

    conn = sqlite3.connect("shops.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO shops (
        client_name,
        client_email,
        gender,
        phone,
        shop_name,
        niche,
        sub_niche,
        domain,
        shopify_url,
        shop_language,
        product_count,
        status,
        payment_status,
        logo_status,
        created_at,
        request_status,
        config_status,
        final_status
    )
    VALUES (
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
        'Nouvelle demande',
        'En attente',
        'En attente',
        'À faire',
        'En attente',
        datetime('now')
    )
    """, (
    client_name,
    client_email,
    gender,
    phone,
    shop_name,
    niche,
    sub_niche,
    domain,
    shopify_url,
    shop_language,
    product_count
    ))

    conn.commit()
    conn.close()

    return """
    <h1>Demande envoyée</h1>
    <p>Votre demande de création de boutique a bien été enregistrée.</p>
    <p>Notre équipe va maintenant la traiter.</p>
    <a href="/">Retour</a>
    """

@app.route("/shops")
def shops():
    if not login_required():
        return redirect(url_for("login"))

    conn = get_azure_sql_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM shops ORDER BY id DESC")
    rows = cursor.fetchall()

    columns = [column[0] for column in cursor.description]

    shops = [
        dict(zip(columns, row))
        for row in rows
    ]

    shops_with_step = []

    for shop in shops:
        shop_dict = dict(shop)

        if shop["request_status"] != "Acceptée":
            shop_dict["current_step"] = "Demande"

        elif shop["payment_status"] != "Validé":
            shop_dict["current_step"] = "Paiement"

        elif shop["logo_status"] != "Prêt":
            shop_dict["current_step"] = "Logo"

        elif shop["config_status"] != "Terminée":
            shop_dict["current_step"] = "Configuration"

        elif shop["final_status"] != "Validée":
            shop_dict["current_step"] = "Validation finale"

        else:
            shop_dict["current_step"] = "Terminée"

        shops_with_step.append(shop_dict)

    total_shops = len(shops)

    new_requests = sum(
        1 for shop in shops
        if shop["request_status"] == "Nouvelle demande"
    )

    pending_payments = sum(
        1 for shop in shops
        if shop["payment_status"] == "En attente"
    )

    blocked_configs = sum(
        1 for shop in shops
        if shop["config_status"] == "Bloquée"
    )

    validated_shops = sum(
        1 for shop in shops
        if shop["final_status"] == "Validée"
    )

    cursor.close()
    conn.close()

    return render_template(
        "shops.html",
        shops=shops_with_step,
        username=session.get("username"),
        role=session.get("role"),
        total_shops=total_shops,
        new_requests=new_requests,
        pending_payments=pending_payments,
        blocked_configs=blocked_configs,
        validated_shops=validated_shops
    )

@app.route("/shop/<int:shop_id>/edit", methods=["GET", "POST"])
def edit_shop(shop_id):
    if not login_required():
        return redirect(url_for("login"))

    role = session.get("role")
    
    if role == "reader":
        return "Accès refusé : lecture seule", 403

    conn = sqlite3.connect("shops.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM shops
        WHERE id = ?
    """, (shop_id,))

    shop = cursor.fetchone()

    if not shop:
        conn.close()
        return "Boutique introuvable", 404

    if request.method == "POST":

        if role == "super_admin":
            request_status = request.form["request_status"]
            payment_status = request.form["payment_status"]
            logo_status = request.form["logo_status"]
            logo_url = request.form["logo_url"]
            config_status = request.form["config_status"]
            final_status = request.form["final_status"]
            if final_status == "Validée" and shop["config_status"] != "Terminée":
                conn.close()
                return """
                    <h1>Action impossible</h1>
                    <p>La validation finale ne peut pas être validée tant que la configuration de la boutique n'est pas terminée.</p>
                    <a href="/shops">Retour à la liste</a>
                """, 403

            cursor.execute("""
                UPDATE shops
                SET request_status = ?,
                    payment_status = ?,
                    logo_status = ?,
                    logo_url = ?,
                    config_status = ?,
                    final_status = ?
                WHERE id = ?
            """, (
                request_status,
                payment_status,
                logo_status,
                logo_url,
                config_status,
                final_status,
                shop_id
            ))
            
            changes = []

            if shop["request_status"] != request_status:
                changes.append(
                    f"Demande : {shop['request_status']} → {request_status}"
                )

            if shop["payment_status"] != payment_status:
                changes.append(
                    f"Paiement : {shop['payment_status']} → {payment_status}"
                )

            if shop["logo_status"] != logo_status:
                changes.append(
                    f"Logo : {shop['logo_status']} → {logo_status}"
                )

            if shop["logo_url"] != logo_url:
                changes.append(
                    "Lien logo modifié"
                )

            if shop["config_status"] != config_status:
                changes.append(
                    f"Configuration : {shop['config_status']} → {config_status}"
                )

            if shop["final_status"] != final_status:
                changes.append(
                    f"Validation finale : {shop['final_status']} → {final_status}"
                )
            
            if changes:
                action_text = " | ".join(changes)

                cursor.execute("""
                    INSERT INTO shop_history (
                        shop_id,
                        username,
                        role,
                        action,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, datetime('now'))
                """, (
                    shop_id,
                    session.get("username"),
                    session.get("role"),
                    action_text
                ))    

        elif role == "payment":
            if shop["request_status"] != "Acceptée":
                conn.close()
                return """
                    <h1>Action impossible</h1>
                    <p>Le paiement ne peut pas être traité tant que la demande n'est pas acceptée par le Super Admin.</p>
                    <a href="/shops">Retour aux boutiques</a>
                """, 403
            
            payment_status = request.form["payment_status"]

            cursor.execute("""
                UPDATE shops
                SET payment_status = ?
                WHERE id = ?
            """, (
                payment_status,
                shop_id
            ))
            cursor.execute("""
                INSERT INTO shop_history (
                    shop_id,
                    username,
                    role,
                    action,
                    created_at
                )
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (
                shop_id,
                session.get("username"),
                session.get("role"),
                f"Paiement modifié : {shop['payment_status']} → {payment_status}"
            ))

        elif role == "designer":
            if shop["request_status"] != "Acceptée":
                conn.close()
                return """
                    <h1>Action impossible</h1>
                    <p>Le logo ne peut pas être traité tant que la demande n'est pas acceptée.</p>
                    <a href="/shops">Retour aux boutiques</a>
                """, 403

            if shop["payment_status"] != "Validé":
                conn.close()
                return """
                    <h1>Action impossible</h1>
                    <p>Le logo ne peut pas être traité tant que le paiement n'est pas validé.</p>
                    <a href="/shops">Retour aux boutiques</a>
                """, 403
            
            logo_status = request.form["logo_status"]
            logo_url = request.form["logo_url"]

            cursor.execute("""
                UPDATE shops
                SET logo_status = ?,
                    logo_url = ?
                WHERE id = ?
            """, (
                logo_status,
                logo_url,
                shop_id
            ))
            cursor.execute("""
                INSERT INTO shop_history (
                    shop_id,
                    username,
                    role,
                    action,
                    created_at
                )
                VALUES (?, ?, ?, datetime('now'))
            """, (
                shop_id,
                session.get("username"),
                session.get("role"),
                f"Logo modifié : {shop['logo_status']} → {logo_status}"
            ))
        
        elif role == "shop_config":
            config_status = request.form["config_status"]
            if config_status == "En cours":

                if shop["request_status"] != "Acceptée":
                    conn.close()
                    return """
                        <h1>Action impossible</h1>
                        <p>La configuration ne peut pas commencer tant que la demande n'est pas acceptée.</p>
                        <a href="/shops">Retour aux boutiques</a>
                    """, 403

                if shop["payment_status"] != "Validé":
                    conn.close()
                    return """
                        <h1>Action impossible</h1>
                        <p>La configuration ne peut pas commencer tant que le paiement n'est pas validé.</p>
                        <a href="/shops">Retour aux boutiques</a>
                    """, 403

                if shop["logo_status"] != "Prêt":
                    conn.close()
                    return """
                        <h1>Action impossible</h1>
                        <p>La configuration ne peut pas commencer tant que le logo n'est pas prêt.</p>
                        <a href="/shops">Retour aux boutiques</a>
                    """, 403
            
            if config_status == "En cours" and shop["payment_status"] != "Validé":
                conn.close()
                return """
                    <h1>Action impossible</h1>
                    <p>La configuration ne peut pas commencer tant que le paiement n'est pas validé.</p>
                    <a href="/shops">Retour à la liste</a>
                """, 403

            issue_domain = 1 if request.form.get("issue_domain") else 0
            issue_shopify_access = 1 if request.form.get("issue_shopify_access") else 0
            issue_products = 1 if request.form.get("issue_products") else 0
            issue_theme = 1 if request.form.get("issue_theme") else 0
            issue_other = 1 if request.form.get("issue_other") else 0
            if config_status == "Terminée":

                if (
                    issue_domain
                    or issue_shopify_access
                    or issue_products
                    or issue_theme
                    or issue_other
                ):
                    conn.close()
                    return """
                        <h1>Action impossible</h1>
                        <p>La configuration ne peut pas être terminée tant qu'un problème est encore signalé.</p>
                        <a href="/shops">Retour aux boutiques</a>
                    """, 403
            issue_comment = request.form.get("issue_comment", "")

            cursor.execute("""
                UPDATE shops
                SET config_status = ?,
                    issue_domain = ?,
                    issue_shopify_access = ?,
                    issue_products = ?,
                    issue_theme = ?,
                    issue_other = ?,
                    issue_comment = ?
                WHERE id = ?
            """, (
                config_status,
                issue_domain,
                issue_shopify_access,
                issue_products,
                issue_theme,
                issue_other,
                issue_comment,
                shop_id
            ))
            issues = []

            if issue_domain:
                issues.append("Domaine")

            if issue_shopify_access:
                issues.append("Accès Shopify")

            if issue_products:
                issues.append("Produits")

            if issue_theme:
                issues.append("Thème")

            if issue_other:
                issues.append("Autre")

            issues_text = ", ".join(issues) if issues else "Aucun problème"

            cursor.execute("""
                INSERT INTO shop_history (
                    shop_id,
                    username,
                    role,
                    action,
                    created_at
                )
                VALUES (?, ?, ?, datetime('now'))
            """, (
                shop_id,
                session.get("username"),
                session.get("role"),
                f"Configuration : {shop['config_status']} → {config_status} | Problèmes : {issues_text}"
            ))
        
        elif role == "reader":
            conn.close()
            return "Accès refusé : lecture seule", 403

        conn.commit()
        conn.close()

        return redirect(url_for("shops"))

    conn.close()

    return render_template(
        "edit_shop.html",
        shop=shop,
        role=role
    )

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_azure_sql_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, username, password, role
            FROM users
            WHERE username = ? AND password = ?
        """, (username, password))

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["username"] = user[1]
            session["role"] = user[3]

            return redirect(url_for("shops"))

        error = "Nom d'utilisateur ou mot de passe incorrect."

    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/history")
def history():

    if not login_required():
        return redirect(url_for("login"))

    selected_shop_id = request.args.get("shop_id")
    selected_username = request.args.get("username")
    selected_role = request.args.get("role")

    conn = sqlite3.connect("shops.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, shop_name
        FROM shops
        ORDER BY shop_name
    """)
    
    shops = cursor.fetchall()

    cursor.execute("""
        SELECT DISTINCT username
        FROM shop_history
        ORDER BY username
    """)

    users = cursor.fetchall()

    cursor.execute("""
        SELECT DISTINCT role
        FROM shop_history
        WHERE role IS NOT NULL
        ORDER BY role
    """)

    roles = cursor.fetchall()

    query = """
        SELECT
            shop_history.id,
            shop_history.shop_id,
            shops.shop_name,
            shop_history.username,
            shop_history.role,
            shop_history.action,
            shop_history.created_at
        FROM shop_history
        JOIN shops ON shop_history.shop_id = shops.id
        WHERE 1=1
    """

    params = []

    if selected_shop_id:
        query += " AND shop_history.shop_id = ?"
        params.append(selected_shop_id)

    if selected_username:
        query += " AND shop_history.username = ?"
        params.append(selected_username)

    if selected_role:
        query += " AND shop_history.role = ?"
        params.append(selected_role)

    query += " ORDER BY shop_history.id DESC"

    cursor.execute(query, params)

    history = cursor.fetchall()

    conn.close()

    return render_template(
        "history.html",
        history=history,
        shops=shops,
        users=users,
        roles=roles,
        selected_shop_id=selected_shop_id,
        selected_username=selected_username,
        selected_role=selected_role
    )

@app.route("/shop/<int:shop_id>")
def shop_detail(shop_id):

    if not login_required():
        return redirect(url_for("login"))

    conn = sqlite3.connect("shops.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Récupérer la boutique
    cursor.execute("""
        SELECT *
        FROM shops
        WHERE id = ?
    """, (shop_id,))

    shop = cursor.fetchone()

    if not shop:
        conn.close()
        return "Boutique introuvable", 404

    # Récupérer son historique
    cursor.execute("""
        SELECT *
        FROM shop_history
        WHERE shop_id = ?
        ORDER BY id DESC
    """, (shop_id,))

    history = cursor.fetchall()

    conn.close()

    return render_template(
        "shop_detail.html",
        shop=shop,
        history=history,
        role=session.get("role")
    )

@app.route("/test-azure-sql")
def test_azure_sql():
    try:
        conn = get_azure_sql_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT DB_NAME()")
        database_name = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return f"Connexion Azure SQL réussie ! Base utilisée : {database_name}"

    except Exception as e:
        return f"Erreur Azure SQL : {str(e)}", 500

if __name__ == "__main__":
    init_db()
    migrate_db()
    init_users()
    app.run(debug=True)