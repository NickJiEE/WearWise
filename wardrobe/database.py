import bcrypt
import os
import csv
import requests
import pyotp
import qrcode
import base64
import mysql.connector as mysql
from mysql.connector import Error
from fastapi import HTTPException
from typing import Optional
from dotenv import load_dotenv
from io import BytesIO

load_dotenv()

MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
MYSQL_HOST = os.getenv("MYSQL_HOST")

GEMINI_API_KEY = "AIzaSyBrzgEDhS0AR5ZYi2oAzaTuloo-7PPhwuE"

def get_db_connection():
    """
    Returns a MySQL connection using the environment variables provided.
    """
    conn = mysql.connect(user=MYSQL_USER, password=MYSQL_PASSWORD, host=MYSQL_HOST, database=MYSQL_DATABASE)
    return conn

def hash_password(plain_password: str) -> str:
    # Hash the password using bcrypt
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")

async def create_session(user_id: int, session_id: str) -> bool:
    """Create a new session in the database."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO sessions (id, user_id) VALUES (%s, %s)", (session_id, user_id)
        )
        connection.commit()
        return True
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

async def get_session(session_id: str) -> Optional[dict]:
    """Retrieve session from database."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT *
            FROM sessions s
            WHERE s.id = %s
        """,
            (session_id,),
        )
        return cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

async def delete_session(session_id: str) -> bool:
    """Delete a session from the database."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
        connection.commit()
        return True
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

async def get_user_id_from_session(session_id: str):
    # Connect to the database to retrieve the user_id based on session_id
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id FROM sessions WHERE id = %s", (session_id,))
    session = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if session:
        return session["user_id"]
    return None

def create_tables():
    """
    Create the tables if they don't already exist.
    """
    create_table_query = """
    CREATE TABLE IF NOT EXISTS {table_name} (
        id INT AUTO_INCREMENT PRIMARY KEY,
        temp FLOAT,
        unit VARCHAR(10),
        timestamp DATETIME,
        device_id VARCHAR(50) NOT NULL DEFAULT 'NONE'
    )
    """

    tables = ["temperature"]

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        for table in tables:
            cursor.execute(create_table_query.format(table_name=table))
        conn.commit()
    except Error as e:
        print(f"Error creating tables: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def create_user_and_session_tables():
    """
    Create the 'users' and 'sessions' tables if they don't already exist.
    The users table stores user information.
    The sessions table stores a session id for each logged-in user,
    along with the user_id and a timestamp.
    """
    create_users_query = """
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        location VARCHAR(255),
        totp_secret VARCHAR(32),
        totp_enabled BOOLEAN DEFAULT 0
    )
    """
    create_sessions_query = """
    CREATE TABLE IF NOT EXISTS sessions (
        id VARCHAR(36) PRIMARY KEY,
        user_id INT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(create_users_query)
        cursor.execute(create_sessions_query)
        conn.commit()
    except Error as e:
        print(f"Error creating tables: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def create_devices_table():
    """
    Create the 'devices' table if it doesn't already exist.
    This table stores device information associated with specific users.
    """
    create_devices_query = """
    CREATE TABLE IF NOT EXISTS devices (
        id INT AUTO_INCREMENT PRIMARY KEY,
        device_id VARCHAR(255) NOT NULL,
        user_id INT NOT NULL,
        name VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE KEY user_device_unique (user_id, device_id)
    )
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(create_devices_query)
        conn.commit()
    except Error as e:
        print(f"Error creating devices table: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def create_closet_table():
    """
    Create the 'closet' table if it doesn't already exist.
    The table stores each cloth's name and type for a given user.
    """
    create_closet_query = """
    CREATE TABLE IF NOT EXISTS closet (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        cloth_type VARCHAR(255) NOT NULL,
        user_id INT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(create_closet_query)
        conn.commit()
    except Error as e:
        print(f"Error creating closet table: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def seed_data_from_csv(table_name: str, csv_path: str):
    """
    Given a table name and path to a CSV file,
    load data from CSV and insert it into the corresponding table.
    The CSV is assumed to have columns: value, unit, timestamp (header row).
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        insert_query = f"""
            INSERT INTO {table_name} (value, unit, timestamp)
            VALUES (%s, %s, %s)
        """

        with open(csv_path, mode="r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            rows_to_insert = []
            for row in reader:
                value = row.get("value")
                unit = row.get("unit")
                timestamp = row.get("timestamp")

                value = float(value) if value else None

                rows_to_insert.append((value, unit, timestamp))

        cursor.executemany(insert_query, rows_to_insert)
        conn.commit()

    except Error as e:
        print(f"Error seeding data for table {table_name}: {e}")
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

def create_and_seed_tables():
    """
    Main function to be called at startup:
    1) Create the tables if not exist
    2) Seed each table from its CSV file
    """
    create_tables()
    create_user_and_session_tables()
    create_devices_table() 
    create_closet_table()

    sensor_csv_mapping = {
        "temperature": "wardrobe/sample/temperature.csv"
    }

    for sensor, csv_file in sensor_csv_mapping.items():
        seed_data_from_csv(sensor, csv_file)

# Get clothing recommendation from Gemini LLM API
def get_clothing_recommendation(city: str, weather: str, temp: float) -> str:
    """
    Call the Gemini LLM API with a prompt to get a clothing recommendation based on the city and weather.
    """
    prompt = f"The weather in {city} is {weather}, and temperature is {temp}. What type of clothes should I wear today? Start your response with 'Hello my pookie 😊' as a new line, the rest remain the same where you include bullet points."
    
    # Build the API URL with the key as a query parameter
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    response = requests.post(api_url, headers=headers, json=payload)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to get recommendation from LLM")
    
    result = response.json()
    
    try:
        # Extract recommendation text from the response.
        # According to the error, result["candidates"][0]["content"] is a dict like:
        # { "parts": [{"text": "..." }], "role": "model" }
        recommendation_data = result["candidates"][0]["content"]
        recommendation = recommendation_data["parts"][0]["text"]
    except (KeyError, IndexError):
        recommendation = "No recommendation available at the moment."
    
    return recommendation

# TOTP Helper Functions
def generate_totp_secret():
    """Generate a new TOTP secret"""
    return pyotp.random_base32()

def get_totp_uri(secret, email, issuer="WearWise"):
    """Generate the TOTP URI for QR code generation"""
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)

def generate_totp_qr_code(totp_uri):
    """Generate a QR code for TOTP setup"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

def verify_totp_code(secret, code):
    """Verify a TOTP code against a secret"""
    totp = pyotp.TOTP(secret)
    return totp.verify(code)

async def enable_totp_for_user(user_id, secret):
    """Enable TOTP for a user by storing the secret"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE users SET totp_secret = %s, totp_enabled = 1 WHERE id = %s",
            (secret, user_id)
        )
        connection.commit()
        return True
    except Error as e:
        print(f"Error enabling TOTP: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

async def disable_totp_for_user(user_id):
    """Disable TOTP for a user"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE users SET totp_secret = NULL, totp_enabled = 0 WHERE id = %s",
            (user_id,)
        )
        connection.commit()
        return True
    except Error as e:
        print(f"Error disabling TOTP: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

async def get_user_totp_status(user_id):
    """Check if a user has TOTP enabled and return their secret if so"""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT totp_enabled, totp_secret FROM users WHERE id = %s",
            (user_id,)
        )
        result = cursor.fetchone()
        return result
    except Error as e:
        print(f"Error getting TOTP status: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
    """
    Create the 'users' and 'sessions' tables if they don't already exist.
    The users table stores user information.
    The sessions table stores a session id for each logged-in user,
    along with the user_id and a timestamp.
    """
    create_users_query = """
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        location VARCHAR(255)
    )
    """
    create_sessions_query = """
    CREATE TABLE IF NOT EXISTS sessions (
        id VARCHAR(36) PRIMARY KEY,
        user_id INT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(create_users_query)
        cursor.execute(create_sessions_query)
        conn.commit()
    except Error as e:
        print(f"Error creating tables: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
