from flask import Flask, g, request, jsonify, render_template, redirect, url_for, flash, session
import mysql.connector
from mysql.connector import Error
import config
from datetime import datetime
import hashlib
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)

app.secret_key = 'Pan America'
app.config.from_object(config)

# Function to connect to the database
def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DB'],
            port=app.config['MYSQL_PORT']
        )
    return g.db

# Route for home page
@app.route('/')
def home():
    return render_template('index.html')

# Route to search for flights
@app.route('/search_flights', methods=['GET'])
def search_flights():
    source_city = request.args.get('source_city')
    destination_city = request.args.get('destination_city')
    date = request.args.get('date')  # expecting format YYYY-MM-DD

    if not source_city and not destination_city and not date:
        return jsonify({"error": "At least one parameter (source_city, destination_city, or date) is required"}), 400

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Build the query dynamically based on available parameters
        query = """
            SELECT f.airline_name, f.flight_num, f.departure_airport, f.departure_time, 
                   f.arrival_airport, f.arrival_time, f.status, f.price
            FROM flight f
            JOIN airport dep_airport ON f.departure_airport = dep_airport.airport_name
            JOIN airport arr_airport ON f.arrival_airport = arr_airport.airport_name
            WHERE 1=1
        """
        params = []

        # Add conditions based on the provided parameters
        if source_city:
            query += " AND dep_airport.airport_city = %s"
            params.append(source_city)

        if destination_city:
            query += " AND arr_airport.airport_city = %s"
            params.append(destination_city)

        if date:
            query += " AND DATE(f.departure_time) = %s"
            params.append(date)


        query += " ORDER BY f.departure_time;"

        # Execute the query with the dynamic parameters
        cursor.execute(query, tuple(params))

        flights = cursor.fetchall()
        conn.close()

        if not flights:
            return jsonify({"message": "No flights found."}), 200

        return jsonify(flights), 200

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500

# Route to view flight status
@app.route('/flight_status', methods=['GET'])
def flight_status():
    flight_num = request.args.get('flight_num')
    date = request.args.get('date')  # expecting format YYYY-MM-DD

    if not flight_num or not date:
        return jsonify({"error": "Missing parameters"}), 400

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT f.airline_name, f.flight_num, f.departure_airport, f.departure_time, 
                   f.arrival_airport, f.arrival_time, f.status, f.price
            FROM flight f
            WHERE f.flight_num = %s 
              AND (DATE(f.departure_time) = %s OR DATE(f.arrival_time) = %s);
        """, (flight_num, date, date))

        flight_status = cursor.fetchone()
        conn.close()

        if not flight_status:
            return jsonify({"message": "Flight not found."}), 200

        return jsonify(flight_status), 200

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500

@app.route('/register')
def register():
    return render_template('register.html')

def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

@app.route('/register_customer', methods=['POST'])
def register_customer():
    # Collect customer details from the form
    name = request.form.get('customer_name')
    email = request.form.get('customer_email')
    password = request.form.get('customer_password')
    building_number = request.form.get('customer_building_number')
    street = request.form.get('customer_street')
    city = request.form.get('customer_city')
    state = request.form.get('customer_state')
    phone = request.form.get('customer_phone')
    passport_number = request.form.get('customer_passport_number')
    passport_expiration = request.form.get('customer_passport_expiration')
    passport_country = request.form.get('customer_passport_country')
    date_of_birth = request.form.get('customer_dob')

    # Debug: Print the received data
    logging.debug(f"Received data: {name}, {email}, {building_number}, {street}, {city}, {state}, {phone}, {passport_number}, {passport_expiration}, {passport_country}, {date_of_birth}")
    
    # Hash the password
    hashed_password = hash_password(password)

    # Debug: Print the hashed password (make sure to not log sensitive info like password in production)
    logging.debug(f"Hashed password: {hashed_password}")

    # Save the customer details to the database
    try:
        db = get_db()
        cursor = db.cursor()

        # Log the query before executing
        query = """
            INSERT INTO customer (
                email, name, password, building_number, street, city, state, 
                phone_number, passport_number, passport_expiration, passport_country, 
                date_of_birth
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        logging.debug(f"Executing query: {query}")
        cursor.execute(query, (
            email, name, hashed_password, building_number, street, city, state,
            phone, passport_number, passport_expiration, passport_country, date_of_birth
        ))
        
        db.commit()

        # Log commit confirmation
        logging.debug("Customer details committed to the database.")
        
        flash('Customer registered successfully!')
    except Error as e:
        db.rollback()

        # Log the exception
        logging.error(f"An error occurred: {e}")
        flash(f"An error occurred: {e}")
    finally:
        cursor.close()

    return redirect(url_for('login'))

@app.route('/register_agent', methods=['POST'])
def register_agent():
    # Collect agent details from the form
    email = request.form.get('agent_email')
    password = request.form.get('agent_password')
    booking_agent_id = request.form.get('agent_id')

    # Hash the password
    hashed_password = hash_password(password)

    # Save the booking agent details to the database
    try:
        db = get_db()
        cursor = db.cursor()
        query = """
            INSERT INTO booking_agent (
                email, password, booking_agent_id
            ) VALUES (%s, %s, %s)
        """
        cursor.execute(query, (
            email, hashed_password, booking_agent_id
        ))
        db.commit()
        flash('Booking Agent registered successfully!')
    except Error as e:
        db.rollback()
        flash(f"An error occurred: {e}")
    finally:
        cursor.close()

    return redirect(url_for('login'))


@app.route('/register_staff', methods=['POST'])
def register_staff():
    # Collect staff details from the form
    username = request.form.get('staff_username')
    password = request.form.get('staff_password')
    first_name = request.form.get('staff_first_name')
    last_name = request.form.get('staff_last_name')
    date_of_birth = request.form.get('staff_dob')
    airline_name = request.form.get('staff_airline')

    # Hash the password
    hashed_password = hash_password(password)

    # Save the airline staff details to the database
    try:
        db = get_db()
        cursor = db.cursor()
        query = """
            INSERT INTO airline_staff (
                username, password, first_name, last_name, date_of_birth, airline_name
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            username, hashed_password, first_name, last_name, date_of_birth, airline_name
        ))
        db.commit()
        flash('Airline Staff registered successfully!')
    except Error as e:
        db.rollback()
        flash(f"An error occurred: {e}")
    finally:
        cursor.close()

    return redirect(url_for('login'))


def check_login(username, password, user_type):
    # Hash the password with MD5
    password_hash = hash_password(password)
    logging.debug(f"while login Hashed password: {password_hash}")
    # Connect to database
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Query to check if the user exists with the given username, password, and user type
    query = """
        SELECT * FROM {} 
        WHERE email = %s AND password = %s
    """.format(user_type)
    cursor.execute(query, (username, password_hash))
    
    user = cursor.fetchone()
    cursor.close()
    
    return user  # Returns user if exists, else None

def check_user_exists(username, user_type):
    db = get_db()  # Get the DB connection
    cursor = db.cursor(dictionary=True)
    
    try:
        if user_type == 'customer':
            cursor.execute("SELECT * FROM customer WHERE email = %s", (username,))
        elif user_type == 'booking_agent':
            cursor.execute("SELECT * FROM booking_agent WHERE email = %s", (username,))
        elif user_type == 'airline_staff':
            cursor.execute("SELECT * FROM airline_staff WHERE username = %s", (username,))
        else:
            return False  # Invalid user_type

        user = cursor.fetchone()  # Fetch one result
        return user is not None
    finally:
        cursor.close()  # Close the cursor after the query


def check_password(username, password, user_type):
    # Get the database connection from g
    db = get_db()

    # Use the connection to create a cursor and perform the query
    cursor = db.cursor(dictionary=True)
    
    try:
        if user_type == 'customer':
            query = "SELECT password FROM customer WHERE email = %s"
            cursor.execute(query, (username,))
        elif user_type == 'booking_agent':
            query = "SELECT password FROM booking_agent WHERE email = %s"
            cursor.execute(query, (username,))
        elif user_type == 'airline_staff':
            query = "SELECT password FROM airline_staff WHERE username = %s"
            cursor.execute(query, (username,))
        else:
            return False  # Invalid user_type

        # Fetch one result
        user = cursor.fetchone()

        if user:
            # In a real application, you should use a secure method like bcrypt to check hashed passwords
            return user['password'] == password
        return False
    finally:
        cursor.close()  # Always close the cursor after use


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_type = request.form['user_type']
        
        # Authenticate user
        user = check_login(username, password, user_type)
        
        if user:
            # Successful login: start session
            session['username'] = username
            session['user_type'] = user_type
            
            flash("Login successful!", "success")
            
            # Redirect to user home page based on user type
            if user_type == 'customer':
                return redirect(url_for('customer_home'))
            elif user_type == 'booking_agent':
                return redirect(url_for('agent_home'))
            elif user_type == 'airline_staff':
                return redirect(url_for('staff_home'))
        else:
            # Unsuccessful login - provide detailed error message
            # Check if the username exists
            if not check_user_exists(username, user_type):
                flash("User does not exist. Please check your username and user type.", "danger")
            # Check if the password is incorrect
            elif not check_password(username, password, user_type):
                flash("Incorrect password. Please try again.", "danger")
            # If no specific reason, general login failure message
            else:
                flash("Invalid username, password, or user type", "danger")
    
    # If GET request or failed login, show login page
    return render_template('login.html')

@app.route('/customer_home')
def customer_home():
    if 'username' in session and session.get('user_type') == 'customer':
        # Example: Fetch upcoming flights for the customer
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT f.flight_num, f.departure_airport, f.arrival_airport, f.departure_time, f.arrival_time
            FROM flight f
            JOIN ticket t ON f.airline_name = t.airline_name AND f.flight_num = t.flight_num
            JOIN purchases p ON t.ticket_id = p.ticket_id
            WHERE p.customer_email = %s AND f.departure_time > NOW()
        """, (session['username'],))
        upcoming_flights = cursor.fetchall()
        
        cursor.close()
        
        # Render customer home page template with any flashed messages and upcoming flights
        return render_template('customer_home.html', upcoming_flights=upcoming_flights)
    else:
        return redirect(url_for('login'))


@app.route('/agent_home')
def agent_home():
    if 'username' in session and session.get('user_type') == 'booking_agent':
        # Render the booking agent home page template
        return render_template('agent_home.html')
    else:
        return redirect(url_for('login'))


@app.route('/staff_home')
def staff_home():
    if 'username' in session and session.get('user_type') == 'airline_staff':
        # Render the airline staff home page template
        return render_template('staff_home.html')
    else:
        return redirect(url_for('login'))


@app.route('/view_purchases')
def view_purchases():
    # Check if the user is logged in
    if 'username' not in session:
        flash("You must be logged in to view purchases.")
        return redirect(url_for('login'))

    user_type = session.get('user_type')
    db = get_db()
    cursor = db.cursor(dictionary=True)

    purchases = []
    try:
        if user_type == 'customer':
            # Query for customers to view their own purchases
            query = """
            SELECT purchases.ticket_id, purchases.purchase_date,
                   flight.airline_name, flight.flight_num, flight.departure_time, flight.arrival_time,
                   flight.departure_airport, flight.arrival_airport, flight.price, flight.status
            FROM purchases
            JOIN ticket ON purchases.ticket_id = ticket.ticket_id
            JOIN flight ON ticket.flight_num = flight.flight_num AND ticket.airline_name = flight.airline_name
            WHERE purchases.customer_email = %s
            """
            cursor.execute(query, (session['username'],))
        elif user_type == 'booking_agent':
            # Query for booking agents to view purchases for their customers
            query = """
            SELECT purchases.ticket_id, purchases.customer_email, purchases.purchase_date,
                   flight.airline_name, flight.flight_num, flight.departure_time, flight.arrival_time,
                   flight.departure_airport, flight.arrival_airport, flight.price, flight.status,
                   customer.name AS customer_name, customer.phone_number
            FROM purchases
            JOIN ticket ON purchases.ticket_id = ticket.ticket_id
            JOIN flight ON ticket.flight_num = flight.flight_num AND ticket.airline_name = flight.airline_name
            JOIN customer ON purchases.customer_email = customer.email
            WHERE purchases.booking_agent_id = %s
            """
            cursor.execute(query, (session['agent_id'],))  # Assuming agent_id is stored in the session
        else:
            flash("User type not recognized.")
            return redirect(url_for('login'))

        purchases = cursor.fetchall()
    except Exception as e:
        flash(f"Error retrieving purchases: {e}")
    finally:
        cursor.close()

    # Render the appropriate template based on the user type
    if user_type == 'customer':
        return render_template('view_customer_purchases.html', purchases=purchases)
    elif user_type == 'booking_agent':
        return render_template('view_agent_purchases.html', purchases=purchases)

    return redirect(url_for('login'))


# Logout route to clear session
@app.route('/logout')
def logout():
    session.clear()
    #flash("You have been logged out", "info")
    return redirect(url_for('login'))

# Close the database connection after each request
@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

if __name__ == '__main__':
    app.run(debug=True)
