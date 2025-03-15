import uvicorn
import uuid
import os
import bcrypt
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, status, Query, Form, Body, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from database import (get_db_connection, create_and_seed_tables, 
                      hash_password, create_session, get_session, 
                      delete_session, get_user_id_from_session, 
                      get_clothing_recommendation)

# TOTP imports
from database import (generate_totp_secret, get_totp_uri, generate_totp_qr_code, 
                      verify_totp_code, enable_totp_for_user, disable_totp_for_user,
                      get_user_totp_status)

app = FastAPI()

devices: List[str] = []

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

dashboard_file = os.path.join(os.path.dirname(__file__), "dashboard.html")

async def get_current_session(request: Request):
    session_id = request.cookies.get("sessionId")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return session

def parse_datetime_to_mysql(dt_string: str) -> str:
    """
    Converts an ISO8601 or 'YYYY-MM-DD HH:MM:SS' formatted datetime string
    into the MySQL datetime format 'YYYY-MM-DD HH:MM:SS'.
    """
    try:
        dt = datetime.fromisoformat(dt_string)
    except Exception:
        try:
            dt = datetime.strptime(dt_string.replace("T", " "), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValueError(f"Invalid datetime format: {dt_string}")
    return dt.strftime("%Y-%m-%d %H:%M:%S")

# Index page
@app.get("/", response_class=HTMLResponse)
def get_html() -> HTMLResponse:
  with open("wardrobe/index.html") as html:
    return HTMLResponse(content=html.read())

# Register page
@app.get("/signup", response_class=HTMLResponse)
def get_register() -> HTMLResponse:
    with open("wardrobe/signup.html") as html:
        return HTMLResponse(content=html.read())

@app.post("/signup")
def register(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    location: str = Form(...)
):
    # Validate password and confirmation match
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if the email already exists
    check_query = "SELECT * FROM users WHERE email = %s"
    cursor.execute(check_query, (email,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Email is already registered")
    
    # Hash the password
    hashed_password = hash_password(password)
    
    # Insert the new user into the database
    insert_query = "INSERT INTO users (name, email, password, location) VALUES (%s, %s, %s, %s)"
    cursor.execute(insert_query, (name, email, hashed_password, location))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    # Redirect to the login page after successful registration
    return RedirectResponse(url="/login", status_code=302)

# Login page
@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    # Optionally, check if user is already logged in by inspecting the session cookie
    session_id = request.cookies.get("sessionId")
    if session_id:
        session = await get_session(session_id)
        if session:
            return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    # Otherwise, serve the login page
    with open("wardrobe/login.html") as html:
        return HTMLResponse(content=html.read())
    
@app.post("/login")
async def login(request: Request):
    # Get form data
    form = await request.form()
    email = form.get("email")
    password = form.get("password")
    totp_code = form.get("totp_code")  # This might be None initially
    
    # Connect to the database and look up the user by email
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM users WHERE email = %s"
    cursor.execute(query, (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    # Validate user and password
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")
    
    if not bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    
    # Check if TOTP is enabled for this user
    if user.get("totp_enabled"):
        # If TOTP code was not provided in this request
        if not totp_code:
            return JSONResponse(
                status_code=200,
                content={"requires_totp": True, "user_id": user["id"]}
            )
        
        # Verify TOTP code
        if not verify_totp_code(user["totp_secret"], totp_code):
            raise HTTPException(status_code=400, detail="Invalid TOTP code")

    # Create a new session
    session_id = str(uuid.uuid4())
    await create_session(user["id"], session_id)
    
    # Create a redirect response, set the session cookie, and redirect to the dashboard
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="sessionId", value=session_id)
    return response

# Add a route to verify TOTP code after initial login
@app.post("/verify-totp")
async def verify_totp(user_id: int = Form(...), totp_code: str = Form(...)):
    # Get the user's TOTP secret
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT totp_secret FROM users WHERE id = %s AND totp_enabled = 1"
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not user or not user["totp_secret"]:
        raise HTTPException(status_code=400, detail="TOTP not enabled for this user")
    
    # Verify the TOTP code
    if not verify_totp_code(user["totp_secret"], totp_code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    
    # Create a new session
    session_id = str(uuid.uuid4())
    await create_session(user_id, session_id)
    
    # Create a redirect response, set the session cookie, and redirect to the dashboard
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="sessionId", value=session_id)
    return response

# Add TOTP setup page route
@app.get("/totp-setup", response_class=HTMLResponse)
async def get_totp_setup(current_session: dict = Depends(get_current_session)):
    """
    Serve the TOTP setup page for the authenticated user.
    """
    with open("wardrobe/totp-setup.html") as f:
        content = f.read()
    return HTMLResponse(content=content)

# API for TOTP setup
@app.get("/api/totp/setup", response_model=Dict[str, Any])
async def setup_totp(current_session: dict = Depends(get_current_session)):
    user_id = current_session["user_id"]
    
    # Get user email
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT email FROM users WHERE id = %s"
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate a new TOTP secret
    secret = generate_totp_secret()
    
    # Generate TOTP URI for QR code
    totp_uri = get_totp_uri(secret, user["email"])
    
    # Generate QR code image as base64
    qr_code = generate_totp_qr_code(totp_uri)
    
    return {
        "secret": secret,
        "qr_code": qr_code
    }

# Add endpoint to enable TOTP
@app.post("/api/totp/enable")
async def enable_totp(
    secret: str = Form(...),
    verification_code: str = Form(...),
    current_session: dict = Depends(get_current_session)
):
    user_id = current_session["user_id"]
    
    # Verify the provided TOTP code before enabling
    if not verify_totp_code(secret, verification_code):
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    # Enable TOTP for the user
    success = await enable_totp_for_user(user_id, secret)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to enable TOTP")
    
    return {"message": "TOTP successfully enabled"}

# Add endpoint to disable TOTP
@app.post("/api/totp/disable")
async def disable_totp(
    verification_code: str = Form(...),
    current_session: dict = Depends(get_current_session)
):
    user_id = current_session["user_id"]
    
    # Get user's current TOTP status
    totp_status = await get_user_totp_status(user_id)
    if not totp_status or not totp_status["totp_enabled"]:
        raise HTTPException(status_code=400, detail="TOTP is not enabled for this user")
    
    # Verify the provided TOTP code before disabling
    if not verify_totp_code(totp_status["totp_secret"], verification_code):
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    # Disable TOTP for the user
    success = await disable_totp_for_user(user_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to disable TOTP")
    
    return {"message": "TOTP successfully disabled"}

# Add endpoint to check if TOTP is enabled
@app.get("/api/totp/status")
async def get_totp_status(current_session: dict = Depends(get_current_session)):
    user_id = current_session["user_id"]
    totp_status = await get_user_totp_status(user_id)
    
    if not totp_status:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"totp_enabled": totp_status["totp_enabled"]}

# Logout page
@app.get("/logout")
async def logout(request: Request):
    # Retrieve the session ID from the "sessionId" cookie
    session_id = request.cookies.get("sessionId")
    
    if session_id:
        # Delete the session record from the database (if using async delete_session)
        await delete_session(session_id)
    
    # Create a redirect response to /login
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    
    # Delete the correct cookie ("sessionId")
    response.delete_cookie("sessionId")
    
    return response

@app.post("/logout")
async def logout(request: Request):
    """
    Clear the user's session and redirect to the login page.
    """
    # Retrieve the session ID from cookies
    session_id = request.cookies.get("sessionId")
    
    # Optionally, if you store sessions in your database, delete the session
    if session_id:
        await delete_session(session_id)  # Ensure delete_session is async
    
    # Create a redirect response to the login page
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    
    # Delete the session cookie
    response.delete_cookie("sessionId")
    
    return response

@app.on_event("startup")
def on_startup():
    """
    This function is called when the application starts.
    It will create and seed the tables in MySQL.
    """
    create_and_seed_tables()

# Fetch the dashboard
@app.get("/dashboard", response_class=HTMLResponse)
async def read_dashboard(current_session: dict = Depends(get_current_session)):
    # Only reached if session is valid
    with open("wardrobe/dashboard.html") as f:
        content = f.read()
    return HTMLResponse(content=content)

# Fetch the profile page
@app.get("/profile", response_class=HTMLResponse)
async def get_profile(current_session: dict = Depends(get_current_session)):
    with open("wardrobe/profile.html") as f:
        content = f.read()
    return HTMLResponse(content=content)

# Fetch all devices
@app.get("/api/devices")
async def get_user_devices(current_session: dict = Depends(get_current_session)):
    """
    Retrieve all devices associated with the current user.
    """
    # Get user ID from the session
    user_id = current_session["user_id"]
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT id, device_id, name FROM devices WHERE user_id = %s"
    cursor.execute(query, (user_id,))
    devices = cursor.fetchall()
    cursor.close()
    conn.close()
    return devices

# Add a device
@app.post("/api/devices/add")
async def add_user_device(
    device_id: str = Body(...), 
    name: Optional[str] = Body(None),
    current_session: dict = Depends(get_current_session)
):
    """
    Add a new device for the current user.
    """
    if not device_id:
        raise HTTPException(status_code=400, detail="Device ID is required")
        
    
    # Get user ID from the session
    user_id = current_session["user_id"]
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Check if the device already exists for this user
    check_query = "SELECT user_id FROM devices WHERE device_id = %s"
    cursor.execute(check_query, (device_id,))
    row = cursor.fetchone()
    if row and row["user_id"] != user_id:
        raise HTTPException(status_code=400, detail="Device already registered to another user")
    
    # Insert the new device
    device_name = name if name else device_id
    insert_query = "INSERT INTO devices (device_id, user_id, name) VALUES (%s, %s, %s)"
    cursor.execute(insert_query, (device_id, user_id, device_name))
    conn.commit()
    
    new_id = cursor.lastrowid
    cursor.close()
    conn.close()
    
    return {
        "message": "Device added successfully", 
        "id": new_id, 
        "device_id": device_id,
        "name": device_name
    }

# Delete a device
@app.post("/api/devices/delete")
async def delete_user_device(
    device_id: str = Body(..., embed=True),
    current_session: dict = Depends(get_current_session)
):
    """
    Delete a device for the current user.
    """
    if not device_id:
        raise HTTPException(status_code=400, detail="Device ID is required")
    
    # Get user ID from the session
    user_id = current_session["user_id"]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Delete the device only if it belongs to the current user
    delete_query = "DELETE FROM devices WHERE user_id = %s AND device_id = %s"
    cursor.execute(delete_query, (user_id, device_id))
    conn.commit()
    
    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Device not found or not owned by this user")
    
    cursor.close()
    conn.close()
    
    return {"message": "Device deleted successfully", "device_id": device_id}

@app.get("/wardrobe", response_class=HTMLResponse)
async def get_wardrobe(current_session: dict = Depends(get_current_session)):
    with open("wardrobe/wardrobe.html", "r") as f:
        content = f.read()
    return HTMLResponse(content=content)

@app.get("/api/ai/clothes", response_model=Dict[str, str])
def get_clothing_ai(city: str = Query(..., description="City name"),
                    weather: str = Query(..., description="Current weather description"),
                    temp: float = Query(..., description="Current temperature")):
    """
    Returns a clothing recommendation based on the provided city and weather.
    """
    recommendation = get_clothing_recommendation(city, weather, temp)
    return {"recommendation": recommendation}

@app.get("/api/user", response_model=Dict[str, Any])
async def get_current_user(request: Request):
    # Retrieve the sessionId from the cookies
    session_id = request.cookies.get("sessionId")
    if not session_id:
        raise HTTPException(status_code=401, detail="User not logged in")
    
    # Check the session to get the user ID
    user_id = await get_user_id_from_session(session_id)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session invalid or expired")
    
    # Query the database to get additional user details (e.g., location)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT id, location FROM users WHERE id = %s"
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Return user_id and location
    return {"user_id": user["id"], "location": user["location"]}

@app.get("/api/closet", response_model=List[Dict[str, Any]])
async def get_closet(request: Request):
    """
    Retrieve all closet (wardrobe) items for the currently logged-in user.
    The user_id is obtained from the cookies.
    """
    # Retrieve user_id from cookies
    session_id = request.cookies.get("sessionId")

    if not session_id:
        raise HTTPException(status_code=401, detail="User not logged in")
    
    # Now, check the session to get the user ID
    user_id = await get_user_id_from_session(session_id)
    
    # Query the database for clothes associated with the user_id
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM closet WHERE user_id = %s"
    cursor.execute(query, (user_id,))
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return items

@app.post("/api/closet/add")
def add_cloth(
    name: str = Body(...),
    cloth_type: str = Body(...),
    user_id: int = Body(...),
):
    """
    Add a new cloth item to the closet.
    Expects the cloth name, type, and the user's id.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    insert_query = """
        INSERT INTO closet (name, cloth_type, user_id)
        VALUES (%s, %s, %s)
    """
    cursor.execute(insert_query, (name, cloth_type, user_id))
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return {"id": new_id, "name": name, "cloth_type": cloth_type}

@app.post("/api/closet/delete")
def delete_cloth(cloth_id: int = Body(...)):
    print(f"Deleting cloth with ID: {cloth_id}")
    """
    Delete a cloth item from the closet using its unique id.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    delete_query = "DELETE FROM closet WHERE id = %s"
    cursor.execute(delete_query, (cloth_id,))
    conn.commit()
    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Cloth not found")
    cursor.close()
    conn.close()
    return {"message": "Cloth deleted successfully", "id": cloth_id}

@app.put("/api/closet/update")
def update_cloth(
    cloth_id: int = Body(...),
    name: Optional[str] = Body(None),
    cloth_type: Optional[str] = Body(None)
):
    """
    Update a cloth record in the closet. Provide the cloth_id and at least one field to update.
    """
    if name is None and cloth_type is None:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    fields = []
    params = []
    if name is not None:
        fields.append("name = %s")
        params.append(name)
    if cloth_type is not None:
        fields.append("cloth_type = %s")
        params.append(cloth_type)
    
    params.append(cloth_id)
    update_query = f"UPDATE closet SET {', '.join(fields)} WHERE id = %s"
    cursor.execute(update_query, tuple(params))
    conn.commit()
    
    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Cloth not found")
    
    cursor.close()
    conn.close()
    return {"message": "Cloth updated successfully", "id": cloth_id}

# Fetch all records for a sensor type
@app.get("/api/temperature")
def get_all_data(
    order_by: Optional[str] = Query(None, alias="order-by"),
    start_date: Optional[str] = Query(None, alias="start-date"),
    end_date: Optional[str] = Query(None, alias="end-date"),
    current_session: dict = Depends(get_current_session),
    request: Request = None
):
    # Retrieve user_id from cookies or session (modify according to your auth system)
    user_id = current_session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not logged in")
    
    # Get the device IDs for this user from the devices table
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT device_id FROM devices WHERE user_id = %s", (user_id,))
    device_rows = cursor.fetchall()
    cursor.close()
    
    device_ids = [row["device_id"] for row in device_rows]
    if not device_ids:
        conn.close()
        return []  # No devices registered, so no data to display
    
    # Build query to filter temperature data by these device IDs
    base_query = "SELECT * FROM temperature WHERE device_id IN ({})".format(
        ", ".join(["%s"] * len(device_ids))
    )
    params = device_ids
    
    if start_date:
        start_date = start_date.replace("T", " ")
        base_query += " AND timestamp >= %s"
        params.append(start_date)
    
    if end_date:
        end_date = end_date.replace("T", " ")
        base_query += " AND timestamp <= %s"
        params.append(end_date)
    
    if order_by in ["temp", "timestamp"]:
        base_query += f" ORDER BY {order_by}"
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute(base_query, params)
    rows = cursor.fetchall()
    
    for row in rows:
        ts = row["timestamp"]
        if isinstance(ts, datetime):
            row["timestamp"] = ts.strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.close()
    conn.close()
    return rows

# Create a new record
@app.post("/api/temperature")
def create_data(data: dict):
    """
    Inserts a new temperature record.
    Expected JSON body:
    {
      "temp": float,
      "unit": string,
      "timestamp": optional, "YYYY-MM-DD HH:MM:SS" or ISO8601 format,
      "device_id": string  -- must be registered via /api/devices/add
    }
    """
    temp = data.get("temp")
    unit = data.get("unit")
    timestamp = data.get("timestamp")
    device_id = data.get("device_id")
    
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id is required")
    
    # Check if the device_id is registered for any user
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id FROM devices WHERE device_id = %s", (device_id,))
    device_info = cursor.fetchone()
    cursor.close()
    
    if not device_info:
        conn.close()
        raise HTTPException(status_code=400, detail="Device not registered")
    
    # Optionally, you can also use the returned user_id from device_info to associate the sensor reading with that user.
    if timestamp:
        try:
            timestamp = parse_datetime_to_mysql(timestamp)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor = conn.cursor()
    insert_query = """
        INSERT INTO temperature (temp, unit, timestamp, device_id)
        VALUES (%s, %s, %s, %s)
    """
    cursor.execute(insert_query, (temp, unit, timestamp, device_id))
    new_id = cursor.lastrowid
    conn.commit()

    cursor.close()
    conn.close()

    return {"id": new_id}

# Fetch the count of records for a sensor type
@app.get("/api/temperature/count")
def get_count():
    """
    GET: /api/{sensor_type}/count
    Returns the number of rows for that sensor_type.
    """

    conn = get_db_connection()
    cursor = conn.cursor()
    count_query = f"SELECT COUNT(*) FROM temperature"
    cursor.execute(count_query)
    (count,) = cursor.fetchone()

    cursor.close()
    conn.close()

    return count

# Fetch a record by ID
@app.get("/api/temperature/{record_id}")
def get_record(record_id: int):
    """
    GET: /api/{sensor_type}/{id}
    Returns a single record by ID, or 404 if not found.
    """

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = f"SELECT * FROM temperature WHERE id=%s"
    cursor.execute(query, (record_id,))
    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Record not found.")

    return row

# Update a record by ID
@app.put("/api/temperature/{record_id}")
def update_record(record_id: int, data: dict):
    """
    PUT: /api/{sensor_type}/{id}
    Body (any of these optional):
    {
      "value": float,
      "unit": string,
      "timestamp": "YYYY-MM-DD HH:MM:SS" or ISO8601
    }
    """

    fields_to_update = []
    params = []

    if "value" in data:
        fields_to_update.append("value=%s")
        params.append(data["value"])
    if "unit" in data:
        fields_to_update.append("unit=%s")
        params.append(data["unit"])
    if "timestamp" in data:
        try:
            ts_converted = parse_datetime_to_mysql(data["timestamp"])
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        fields_to_update.append("timestamp=%s")
        params.append(ts_converted)

    if not fields_to_update:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    update_query = f"UPDATE temperature SET {', '.join(fields_to_update)} WHERE id=%s"
    params.append(record_id)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(update_query, tuple(params))
    conn.commit()

    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Record not found.")

    cursor.close()
    conn.close()

    return {"status": "success"}

# Delete a record by ID
@app.delete("/api/temperature/{record_id}")
def delete_record(record_id: int):
    """
    DELETE: /api/{sensor_type}/{id}
    Deletes a single record by ID, or returns 404 if not found.
    """

    conn = get_db_connection()
    cursor = conn.cursor()
    delete_query = f"DELETE FROM temperature WHERE id=%s"
    cursor.execute(delete_query, (record_id,))
    conn.commit()

    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Record not found.")

    cursor.close()
    conn.close()

    return {"status": "deleted"}

@app.get("/get_user_location")
async def get_user_location(request: Request, current_session: dict = Depends(get_current_session)):
    # Extract the user_id from the current session
    user_id = current_session.get("user_id")
    
    if not user_id:
        raise HTTPException(status_code=400, detail="Please log in first.")
    
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Execute the query to get the location
    cursor.execute("SELECT location FROM users WHERE id = %s", (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="User location not found")

    return {"location": result["location"]}

@app.get("/contact-us")
def get_contact():
    return FileResponse("wardrobe/contact-us.html")

@app.get("/privacy-policy")
def get_privacy_policy():
    return FileResponse("wardrobe/privacy-policy.html")

@app.get("/terms-and-conditions")
def get_terms():
    return FileResponse("wardrobe/terms-and-conditions.html")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=6543, reload=True)