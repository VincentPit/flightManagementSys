from flask import Flask, g, request, jsonify, render_template, redirect, url_for, flash, session
import mysql.connector
from mysql.connector import Error
import config
from datetime import datetime, timedelta
import hashlib
import logging
import uuid

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
        return redirect(url_for('login'))  # Redirect after successful registration
    except Error as e:
        db.rollback()

        # Log the exception
        logging.error(f"An error occurred: {e}")
        flash(f"An error occurred: {e}")
        return render_template('register.html', error_message=f"An error occurred: {e}")  # Stay on the same page with error message
    finally:
        cursor.close()


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
        return redirect(url_for('login'))  # Redirect after successful registration
    except Error as e:
        db.rollback()
        flash(f"An error occurred: {e}")
        return render_template('register.html', error_message=f"An error occurred: {e}")  # Stay on the same page with error message
    finally:
        cursor.close()


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

    try:
        db = get_db()
        cursor = db.cursor()

        # Save the airline staff details
        staff_query = """
            INSERT INTO airline_staff (
                username, password, first_name, last_name, date_of_birth, airline_name
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(staff_query, (
            username, hashed_password, first_name, last_name, date_of_birth, airline_name
        ))

        # Assign the default "Operator" role
        permission_query = """
            INSERT INTO permission (permission_id, username, permission)
            VALUES (UUID(), %s, %s)
        """
        cursor.execute(permission_query, (username, 'Operator'))
        db.commit()

        # Add the role to the session
        session['roles'] = ['Operator']  # Store initial role in session for newly registered staff

        flash('Airline Staff registered successfully with Operator role!')
        return redirect(url_for('login'))  # Redirect to login page after successful registration
    except Error as e:
        db.rollback()
        logging.error(f"An error occurred while registering staff: {e}")
        flash(f"An error occurred: {e}")
        return render_template('register.html', error_message=f"An error occurred: {e}")  # Stay on the same page with error message
    finally:
        cursor.close()


def check_login(username, password, user_type):
    # Hash the password with MD5
    password_hash = hash_password(password)
    logging.debug(f"while login Hashed password: {password_hash}")
    # Connect to database
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Query to check if the user exists with the given username, password, and user type
    if user_type == "airline_staff":
        query = """
            SELECT * FROM airline_staff
            WHERE username = %s AND password = %s
        """
    else:
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
                db = get_db()
                cursor = db.cursor()
                
                permission_query = """
                        SELECT permission
                        FROM permission
                        WHERE username = %s
                    """
                cursor.execute(permission_query, (username,))
                permissions = cursor.fetchall()
                
                airline_query = """
                        SELECT airline_name 
                        FROM airline_staff
                        WHERE username = %s
                    """
                cursor.execute(airline_query, (username,))
                airlines = cursor.fetchall()
                airline = airlines[0]

                # Store roles in session as a list
                session['roles'] = [perm[0] for perm in permissions]
                session['airline'] = airline[0]
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
        customer_email = session.get('username')
        query = """
                SELECT f.airline_name, f.flight_num, f.departure_airport, f.departure_time, f.arrival_airport, f.arrival_time
                FROM purchases p
                JOIN ticket t ON p.ticket_id = t.ticket_id
                JOIN flight f ON t.airline_name = f.airline_name AND t.flight_num = f.flight_num
                WHERE p.customer_email = %s
                ORDER BY f.departure_time
            """
        cursor.execute(query, (customer_email,))
        flights = cursor.fetchall()
        
        cursor.close()
        
        # Render customer home page template with any flashed messages and upcoming flights
        return render_template('customer_home.html', upcoming_flights=flights)
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
            cursor.execute(query, (session['agent_id'],))  # agent_id is stored in the session
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

@app.route('/view_commission', methods=['GET', 'POST'])
def view_commission():
    if 'username' not in session:
        flash("Please log in to view commission details.")
        return redirect(url_for('login'))
    
    booking_agent_email = session['username']
    
    # Default date range: past 60 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=60)

    if request.method == 'POST':
        # Get custom date range from form if provided
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        if not start_date or not end_date:
            flash("Please provide both start and end dates.")
            return redirect(url_for('view_commission'))
        
        # Convert to date objects for query
        logging.debug("start_end_date", [start_date, end_date])
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    try:
        db = get_db()
        cursor = db.cursor()
        
        # Query to calculate total commission, average commission per ticket, and total tickets sold
        commission_query = """
            SELECT 
                SUM(f.price * 0.1) AS total_commission,
                AVG(f.price * 0.1) AS avg_commission_per_ticket,
                COUNT(p.ticket_id) AS total_tickets_sold
            FROM purchases p
            JOIN ticket t ON p.ticket_id = t.ticket_id
            JOIN flight f ON t.airline_name = f.airline_name AND t.flight_num = f.flight_num
            WHERE p.booking_agent_email = %s
            AND p.purchase_date BETWEEN %s AND %s
        """
        cursor.execute(commission_query, (booking_agent_email, start_date, end_date))
        commission_data = cursor.fetchone()
        logging.debug("commission_data:", commission_data)
        # Render the commission data
        return render_template(
            'view_commission.html',
            commission_data=commission_data,
            start_date=start_date,
            end_date=end_date
        )

    except Error as e:
        logging.error(f"An error occurred while fetching commission data: {e}")
        flash(f"An error occurred: {e}")
    finally:
        cursor.close()

    return render_template('view_commission.html')

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

@app.route('/my_flights', methods=['GET'])
def view_my_flights():
    # Fetch logged-in user's email
    agent_email = None
    customer_email = None
    staff_name = None
    user_type = session.get('user_type')
    
    
    if user_type == "customer":
        logging.debug("view flights customer")
        customer_email = session.get('username')
        
        
    if user_type == "booking_agent":
        logging.debug("view flights booking_agent")
        agent_email = session.get('username')
        
    if user_type == "airline_staff":
        staff_name = session.get('username')
        logging.debug("view flights airline_staff")
    
    #session.get('username')
    if agent_email:
        try:
            db = get_db()
            cursor = db.cursor()

            # Default: Show upcoming flights by joining `purchases`, `ticket`, and `flight` tables
            query = """
                SELECT f.airline_name, f.flight_num, f.departure_airport, f.departure_time, f.arrival_airport, f.arrival_time
                FROM purchases p
                JOIN ticket t ON p.ticket_id = t.ticket_id
                JOIN flight f ON t.airline_name = f.airline_name AND t.flight_num = f.flight_num
                WHERE p.booking_agent_email = %s
                ORDER BY f.departure_time
            """
            cursor.execute(query, (agent_email,))
            
            
            flights = cursor.fetchall()

            # Check if no flights were found
            logging.debug("Fetched FLights:", flights)
            if not flights:
                flash("Hi Agent, you have no upcoming flights.")
            
            return render_template('my_flights.html', flights=flights)
        
        except Error as e:
            logging.error(f"An error occurred: {e}")
            flash(f"An error occurred: {e}")
            return redirect(url_for('home'))  # Redirect to home page or some other page
        
        finally:
            cursor.close()
            

    elif customer_email:
        try:
            db = get_db()
            cursor = db.cursor()

            # Default: Show upcoming flights by joining `purchases`, `ticket`, and `flight` tables
            query = """
                SELECT f.airline_name, f.flight_num, f.departure_airport, f.departure_time, f.arrival_airport, f.arrival_time
                FROM purchases p
                JOIN ticket t ON p.ticket_id = t.ticket_id
                JOIN flight f ON t.airline_name = f.airline_name AND t.flight_num = f.flight_num
                WHERE p.customer_email = %s
                ORDER BY f.departure_time
            """
            cursor.execute(query, (customer_email,))
            flights = cursor.fetchall()

            # Check if no flights were found
            if not flights:
                flash("Dear Customer, you have no upcoming flights.")
            
            return render_template('my_flights.html', flights=flights)
        
        except Error as e:
            logging.error(f"An error occurred: {e}")
            flash(f"An error occurred: {e}")
            return redirect(url_for('home'))  # Redirect to home page or some other page
        
        finally:
            cursor.close()
    elif staff_name:
        try:
            db = get_db()
            cursor = db.cursor()

            # Default: Show upcoming flights by joining `purchases`, `ticket`, and `flight` tables
            query = """
                SELECT f.airline_name, f.flight_num, f.departure_airport, f.departure_time, f.arrival_airport, f.arrival_time
                FROM airline_staff a
                JOIN flight f ON a.airline_name = f.airline_name
                WHERE a.username = %s
                ORDER BY f.departure_time
            """
            cursor.execute(query, (staff_name,))
            flights = cursor.fetchall()

            # Check if no flights were found
            if not flights:
                flash(f"Dear Airline Staff {staff_name}, you have no upcoming flights.")
            
            return render_template('my_flights.html', flights=flights)
        
        except Error as e:
            logging.error(f"An error occurred: {e}")
            flash(f"An error occurred: {e}")
            return redirect(url_for('home'))  # Redirect to home page or some other page
        
        finally:
            cursor.close()
    else:
        flash("Please log in to view your flights.")
        return redirect(url_for('login'))


@app.route('/search_flights_customer', methods=['GET', 'POST'])
def search_flights_customer():
    if request.method == 'POST':
        source = request.form.get('source')
        destination = request.form.get('destination')
        date = request.form.get('date')

        try:
            db = get_db()
            cursor = db.cursor()

            query = """
                SELECT * FROM flight
                WHERE departure_airport LIKE %s AND arrival_airport LIKE %s
                AND departure_time >= %s
            """
            cursor.execute(query, (f"%{source}%", f"%{destination}%", date))
            available_flights = cursor.fetchall()
            
            logging.debug("found available_flights:", available_flights)
            return render_template('search_flights.html', flights=available_flights)

        except Error as e:
            logging.error(f"An error occurred: {e}")
            flash(f"An error occurred: {e}")
        finally:
            cursor.close()

    return render_template('search_flights.html')


@app.route('/purchase_ticket/<airline_name>/<int:flight_num>', methods=['GET'])
def purchase_ticket(airline_name, flight_num):
    customer_email = session.get('username')

    if customer_email:
        try:
            db = get_db()
            cursor = db.cursor()

            # Insert the ticket into the ticket table to get ticket_id
            ticket_query = """
                INSERT INTO ticket (airline_name, flight_num)
                VALUES (%s, %s)
            """
            cursor.execute(ticket_query, (airline_name, flight_num))
            ticket_id = cursor.lastrowid  # Get the generated ticket_id
            
            # Insert the purchase into the purchases table
            purchase_query = """
                INSERT INTO purchases (ticket_id, customer_email, purchase_date)
                VALUES (%s, %s, %s)
            """
            cursor.execute(purchase_query, (ticket_id, customer_email, datetime.now().date()))
            db.commit()
            
            flash('Ticket purchased successfully!')
            return redirect(url_for('view_my_flights'))

        except Error as e:
            logging.error(f"An error occurred: {e}")
            flash(f"An error occurred: {e}")
            db.rollback()  # Rollback in case of error
        finally:
            cursor.close()

    flash("Please log in to purchase a ticket.")
    return redirect(url_for('login'))

@app.route('/search_flights_agent', methods=['GET', 'POST'])
def search_flights_agent():
    if 'username' not in session:
        flash("Please log in to search for flights.")
        return redirect(url_for('login'))

    booking_agent_email = session['username']

    if request.method == 'POST':
        source = request.form.get('source')
        destination = request.form.get('destination')
        date = request.form.get('date')

        try:
            db = get_db()
            cursor = db.cursor()

            # Query to get the airline that the booking agent works for
            agent_airline_query = """
                SELECT airline FROM booking_agent
                WHERE email = %s
            """
            cursor.execute(agent_airline_query, (booking_agent_email,))
            agent_airline = cursor.fetchone()

            if agent_airline:
                airline_name = agent_airline[0]

                # Query to search for flights based on source, destination, date, and airline
                search_query = """
                    SELECT * FROM flight
                    WHERE airline_name = %s
                    AND departure_airport LIKE %s
                    AND arrival_airport LIKE %s
                    AND DATE(departure_time) = %s
                """
                cursor.execute(search_query, (airline_name, f"%{source}%", f"%{destination}%", date))
                available_flights = cursor.fetchall()
                return render_template('search_flights_agent.html', flights=available_flights)

            else:
                flash("Booking agent airline information not found.")

        except Error as e:
            logging.error(f"An error occurred during flight search: {e}")
            flash(f"An error occurred: {e}")
        finally:
            cursor.close()

    return render_template('search_flights_agent.html')


@app.route('/purchase_ticket_agent/<airline_name>/<int:flight_num>', methods=['GET', 'POST'])
def purchase_ticket_agent(airline_name, flight_num):
    if 'username' not in session:
        flash("Please log in to purchase a ticket.")
        return redirect(url_for('login'))

    booking_agent_email = session.get('username')  # Booking agent's email

    if request.method == 'POST':
        customer_emails = request.form.getlist('customer_emails')  # Selected customer emails
        num_tickets = int(request.form.get('num_tickets', 1))  # Number of tickets to purchase

        try:
            db = get_db()
            cursor = db.cursor()

            for _ in range(num_tickets):
                # Insert the ticket for the flight
                ticket_query = """
                    INSERT INTO ticket (airline_name, flight_num)
                    VALUES (%s, %s)
                """
                cursor.execute(ticket_query, (airline_name, flight_num))
                ticket_id = cursor.lastrowid  # Get the generated ticket_id

                # Insert the purchase record for each selected customer
                for customer_email in customer_emails:
                    purchase_query = """
                        INSERT INTO purchases (ticket_id, customer_email, booking_agent_email, purchase_date)
                        VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(purchase_query, (ticket_id, customer_email, booking_agent_email, datetime.now().date()))

            db.commit()
            flash(f'Tickets purchased successfully for {len(customer_emails)} customers!')
            return redirect(url_for('view_my_flights'))

        except Error as e:
            logging.error(f"An error occurred: {e}")
            flash(f"An error occurred: {e}")
            db.rollback()
        finally:
            cursor.close()

    # Retrieve list of customers for agent to select
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT email FROM customer")
        customers = cursor.fetchall()
    except Error as e:
        logging.error(f"An error occurred while fetching customers: {e}")
        flash(f"An error occurred: {e}")
        customers = []
    finally:
        cursor.close()

    return render_template('purchase_ticket_agent.html', airline_name=airline_name, flight_num=flight_num, customers=customers)

@app.route('/track_spending', methods=['GET'])
def track_spending():
    customer_email = session.get('username')
    
    if customer_email:
        try:
            db = get_db()
            cursor = db.cursor()

            # Query to calculate the total money spent per month in the past year
            query = """
                SELECT SUM(f.price) AS total_spent, MONTH(f.departure_time) AS month
                FROM purchases p
                JOIN ticket t ON p.ticket_id = t.ticket_id
                JOIN flight f ON t.airline_name = f.airline_name AND t.flight_num = f.flight_num
                WHERE p.customer_email = %s AND f.departure_time >= CURDATE() - INTERVAL 1 YEAR
                GROUP BY MONTH(f.departure_time)
            """
            cursor.execute(query, (customer_email,))
            spending_data = cursor.fetchall()
            logging.debug("Fetched spending_data: %s", spending_data)
            
            # Render the data for the chart
            return render_template('track_spending.html', spending_data=spending_data)

        except Error as e:
            logging.error(f"An error occurred: {e}")
            flash(f"An error occurred: {e}")
        finally:
            cursor.close()
    else:
        flash("Please log in to track your spending.")
        return redirect(url_for('login'))

@app.route('/view_top_customers', methods=['GET'])
def view_top_customers():
    if 'username' not in session:
        flash("Please log in to view top customers.")
        return redirect(url_for('login'))
    
    booking_agent_email = session['username']
    
    # Calculate date ranges
    six_months_ago = datetime.now().date() - timedelta(days=180)
    one_year_ago = datetime.now().date() - timedelta(days=365)

    try:
        db = get_db()
        cursor = db.cursor()

        # Query for top customers by tickets bought in the past 6 months
        tickets_query = """
            SELECT p.customer_email, COUNT(p.ticket_id) AS tickets_bought
            FROM purchases p
            JOIN ticket t ON p.ticket_id = t.ticket_id
            WHERE p.booking_agent_email = %s
            AND p.purchase_date >= %s
            GROUP BY p.customer_email
            ORDER BY tickets_bought DESC
            LIMIT 5
        """
        cursor.execute(tickets_query, (booking_agent_email, six_months_ago))
        top_customers_by_tickets = cursor.fetchall()

        # Query for top customers by commission received in the last year
        commission_query = """
            SELECT p.customer_email, SUM(f.price * 0.1) AS total_commission
            FROM purchases p
            JOIN ticket t ON p.ticket_id = t.ticket_id
            JOIN flight f ON t.airline_name = f.airline_name AND t.flight_num = f.flight_num
            WHERE p.booking_agent_email = %s
            AND p.purchase_date >= %s
            GROUP BY p.customer_email
            ORDER BY total_commission DESC
            LIMIT 5
        """
        cursor.execute(commission_query, (booking_agent_email, one_year_ago))
        top_customers_by_commission = cursor.fetchall()

        # Render the results in the template
        
        logging.debug('top_customers_by_tickets', top_customers_by_tickets)
        logging.debug("top_customers_by_commission", top_customers_by_commission)
        return render_template(
            'view_top_customers.html',
            top_customers_by_tickets=top_customers_by_tickets,
            top_customers_by_commission=top_customers_by_commission
        )

    except Error as e:
        logging.error(f"An error occurred while fetching top customers: {e}")
        flash(f"An error occurred: {e}")
    finally:
        cursor.close()

    return render_template('view_top_customers.html')

@app.route('/view_my_flights_staff', methods=['GET', 'POST'])
def view_my_flights_staff():
    if 'username' not in session:
        flash("Please log in as staff to view flights.")
        return redirect(url_for('login'))

    username = session['username']
    db = get_db()
    cursor = db.cursor()

    try:
        # Retrieve the airline the staff belongs to
        query = "SELECT airline_name FROM airline_staff WHERE username = %s"
        cursor.execute(query, (username,))
        airline = cursor.fetchone()
        if not airline:
            flash("Airline not found for the current staff user.")
            return redirect(url_for('login'))
        
        airline_name = airline[0]

        # Get date range from the form or default values
        start_date = request.form.get('start_date', datetime.now().date())
        end_date = request.form.get('end_date', (datetime.now() + timedelta(days=30)).date())

        # Query flights for the staff's airline within the specified date range
        query = """
            SELECT * FROM flight
            WHERE airline_name = %s
              AND departure_time BETWEEN %s AND %s
        """
        cursor.execute(query, (airline_name, start_date, end_date))
        flights = cursor.fetchall()

        logging.debug(f"Found Staff Flights: {flights}")
        return render_template('my_flights_staff.html', flights=flights)

    except Error as e:
        logging.error(f"An error occurred while retrieving flights: {e}")
        flash("An error occurred while retrieving flights. Please try again.")
        return render_template('my_flights.html')

    finally:
        cursor.close()

@app.route('/create_flight', methods=['GET', 'POST'])
def create_flight():
    if 'username' not in session or "airline_staff" != session.get('user_type') or 'Admin' not in session.get('roles'):
        flash("Unauthorized access. Only Admins can create flights.")
        return redirect(url_for('staff_home'))

    if request.method == 'POST':
        flight_data = {
            'airline_name': session['airline'],
            'flight_num': request.form.get('flight_num'),
            'departure_airport': request.form.get('departure_airport'),
            'arrival_airport': request.form.get('arrival_airport'),
            'departure_time': request.form.get('departure_time'),
            'arrival_time': request.form.get('arrival_time'),
            'price': float(request.form.get('price')),
            'status': request.form.get('status'),
            'airplane_id': request.form.get('airplane_id')
        }
        
        try:
            db = get_db()
            cursor = db.cursor()

            query = """
                INSERT INTO flight (airline_name, flight_num, departure_airport, arrival_airport, departure_time, arrival_time, price, status, airplane_id)
                VALUES (%(airline_name)s, %(flight_num)s, %(departure_airport)s, %(arrival_airport)s, %(departure_time)s, %(arrival_time)s, %(price)s, %(status)s, %(airplane_id)s)
            """
            cursor.execute(query, flight_data)
            db.commit()
            flash("Flight created successfully!")
            return redirect(url_for('view_my_flights'))

        except Error as e:
            logging.error(f"An error occurred: {e}")
            flash(f"An error occurred: {e}")
            db.rollback()
        finally:
            cursor.close()

    return render_template('create_flight.html')


@app.route('/change_flight_status/<int:flight_num>', methods=['GET', 'POST'])
def change_flight_status(flight_num):
    if 'username' not in session or session.get('user_type') != "airline_staff" or 'Operator' not in session.get('roles'):
        flash("Unauthorized access. Only Operators can change flight status.")
        return redirect(url_for('staff_home'))

    if request.method == 'POST':
        new_status = request.form.get('status')
        try:
            db = get_db()
            cursor = db.cursor()

            query = """
                UPDATE flight
                SET status = %s
                WHERE flight_num = %s AND airline_name = %s
            """
            cursor.execute(query, (new_status, flight_num, session.get('airline')))
            db.commit()
            flash("Flight status updated successfully!")
            return redirect(url_for('view_my_flights'))
        except Error as e:
            logging.error(f"An error occurred: {e}")
            flash(f"An error occurred: {e}")
            db.rollback()
        finally:
            cursor.close()

    return render_template('change_flight_status.html', flight_num=flight_num)


@app.route('/add_airplane', methods=['GET', 'POST'])
def add_airplane():
    if 'username' not in session or session.get('user_type') != "airline_staff" or 'Operator' not in session.get('roles'):
        flash("Unauthorized access. Only Operators can add airplanes.")
        return redirect(url_for('login'))

    airplanes = []
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Fetch airplanes owned by the user's airline
        query = """
            SELECT airplane_id, seats
            FROM airplane
            WHERE airline_name = %s
        """
        cursor.execute(query, (session['airline'],))
        airplanes = cursor.fetchall()
    except Error as e:
        logging.error(f"An error occurred while fetching airplanes: {e}")
        flash(f"An error occurred: {e}")
    finally:
        cursor.close()

    if request.method == 'POST':
        airplane_data = {
            'airplane_id': request.form.get('airplane_id'),
            'seats': request.form.get('seats'),
            'airline_name': session['airline']
        }

        try:
            cursor = db.cursor()
            query = """
                INSERT INTO airplane (airplane_id, seats, airline_name)
                VALUES (%(airplane_id)s, %(seats)s, %(airline_name)s)
            """
            cursor.execute(query, airplane_data)
            db.commit()
            flash("Airplane added successfully!")
            return redirect(url_for('add_airplane'))
        except Error as e:
            logging.error(f"An error occurred: {e}")
            flash(f"An error occurred: {e}")
            db.rollback()
        finally:
            cursor.close()

    return render_template('add_airplane.html', airplanes=airplanes)

@app.route('/add_airport', methods=['GET', 'POST'])
def add_airport():
    if 'username' not in session or session.get('user_type') != "airline_staff" or 'Admin' not in session.get('roles'):
        flash("Unauthorized access. Only Admins can add airports.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        airport_data = {
            'airport_name': request.form.get('airport_name'),
            'city': request.form.get('city'),
        }

        try:
            db = get_db()
            cursor = db.cursor()

            query = """
                INSERT INTO airport (airport_name, airport_city)
                VALUES (%(airport_name)s, %(city)s)
            """
            cursor.execute(query, airport_data)
            db.commit()
            flash("Airport added successfully!")
            return redirect(url_for('staff_home'))
        except Error as e:
            logging.error(f"An error occurred: {e}")
            flash(f"An error occurred: {e}")
            db.rollback()
        finally:
            cursor.close()

    return render_template('add_airport.html')

@app.route('/view_booking_agents')
def view_booking_agents():
    if 'username' not in session or session.get('user_type') != "airline_staff":
        flash("Unauthorized access.")
        return redirect(url_for('login'))

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Top 5 booking agents by tickets sold in the past month (excluding NULL booking_agent_email)
        cursor.execute("""
            SELECT booking_agent_email, COUNT(*) AS tickets_sold
            FROM ticket
            NATURAL JOIN purchases
            WHERE purchase_date >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)
            AND booking_agent_email IS NOT NULL
            GROUP BY booking_agent_email
            ORDER BY tickets_sold DESC
            LIMIT 5
        """)
        top_agents_month = cursor.fetchall()

        # Top 5 booking agents by tickets sold in the past year (excluding NULL booking_agent_email)
        cursor.execute("""
            SELECT booking_agent_email, COUNT(*) AS tickets_sold
            FROM ticket
            NATURAL JOIN purchases
            WHERE purchase_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
            AND booking_agent_email IS NOT NULL
            GROUP BY booking_agent_email
            ORDER BY tickets_sold DESC
            LIMIT 5
        """)
        top_agents_year = cursor.fetchall()

        # Top 5 booking agents by commission earned in the past year (excluding NULL booking_agent_email)
        commission_rate = 0.05  # 5% commission

        cursor.execute("""
            SELECT 
                p.booking_agent_email, 
                COUNT(*) AS tickets_sold,
                SUM(f.price) AS total_sales,
                SUM(f.price) * %s AS commission_earned
            FROM 
                ticket t
            JOIN purchases p ON t.ticket_id = p.ticket_id
            JOIN flight f ON t.airline_name = f.airline_name AND t.flight_num = f.flight_num
            WHERE 
                p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
            AND p.booking_agent_email IS NOT NULL
            GROUP BY 
                p.booking_agent_email
            ORDER BY 
                commission_earned DESC
            LIMIT 5
        """, (commission_rate,))
        
        top_agents_commission = cursor.fetchall()
        logging.debug("COMMISION", top_agents_commission)

    except Error as e:
        logging.error(f"An error occurred: {e}")
        flash(f"An error occurred: {e}")
        return redirect(url_for('staff_home'))
    finally:
        cursor.close()

    return render_template('view_booking_agents.html', 
                           top_agents_month=top_agents_month,
                           top_agents_year=top_agents_year,
                           top_agents_commission=top_agents_commission)


@app.route('/view_frequent_customers')
def view_frequent_customers():
    if 'username' not in session or session.get('user_type') != "airline_staff":
        flash("Unauthorized access.")
        return redirect(url_for('login'))

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Most frequent customer in the last year
        cursor.execute("""
            SELECT customer_email, COUNT(*) AS flights_taken
            FROM ticket NATURAL JOIN purchases NATURAL JOIN flight
            WHERE airline_name = %s AND departure_time >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
            GROUP BY customer_email
            ORDER BY flights_taken DESC
            LIMIT 1
        """, (session['airline'],))
        most_frequent_customer = cursor.fetchone()

        # Fetch all flights for a specific customer
        customer_email = request.args.get('customer_email')
        customer_flights = []
        if customer_email:
            cursor.execute("""
                SELECT flight_num, departure_time, arrival_time, departure_airport, arrival_airport
                FROM ticket NATURAL JOIN purchases NATURAL JOIN flight
                WHERE customer_email = %s AND airline_name = %s
            """, (customer_email, session['airline']))
            customer_flights = cursor.fetchall()

    except Error as e:
        logging.error(f"An error occurred: {e}")
        flash(f"An error occurred: {e}")
        return redirect(url_for('staff_home'))
    finally:
        cursor.close()

    return render_template('view_frequent_customers.html', 
                           most_frequent_customer=most_frequent_customer, 
                           customer_flights=customer_flights)

@app.route('/view_reports', methods=['GET', 'POST'])
def view_reports():
    if 'username' not in session or session.get('user_type') != "airline_staff":
        flash("Unauthorized access.")
        return redirect(url_for('login'))

    tickets_sold_data = []
    last_month_revenue = []
    last_year_revenue = []

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Handle form inputs for date range
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        logging.debug(f"start_date: {start_date}, end_date: {end_date}")

        # Query: Total tickets sold (with optional date range)
        if start_date and end_date:
            query = """
                SELECT DATE(purchase_date) AS sale_date, COUNT(*) AS tickets_sold
                FROM ticket
                NATURAL JOIN purchases
                WHERE purchase_date BETWEEN %s AND %s
                GROUP BY sale_date
                ORDER BY sale_date
            """
            cursor.execute(query, (start_date, end_date))
        else:
            # Default: Last year
            query = """
                SELECT DATE_FORMAT(purchase_date, '%%Y-%%m') AS month, COUNT(*) AS tickets_sold
                FROM ticket
                NATURAL JOIN purchases
                WHERE purchase_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
                GROUP BY month
                ORDER BY month
            """
            cursor.execute(query)
        tickets_sold_data = cursor.fetchall()

        # Query: Revenue comparison for last month
        cursor.execute("""
            SELECT 
                IF(booking_agent_email IS NULL, 'Direct Sales', 'Indirect Sales') AS sale_type,
                SUM(f.price) AS revenue
            FROM 
                ticket t
            JOIN purchases p ON t.ticket_id = p.ticket_id
            JOIN flight f ON t.airline_name = f.airline_name AND t.flight_num = f.flight_num
            WHERE p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)
            GROUP BY sale_type
        """)
        last_month_revenue = cursor.fetchall()

        # Query: Revenue comparison for last year
        cursor.execute("""
            SELECT 
                IF(booking_agent_email IS NULL, 'Direct Sales', 'Indirect Sales') AS sale_type,
                SUM(f.price) AS revenue
            FROM 
                ticket t
            JOIN purchases p ON t.ticket_id = p.ticket_id
            JOIN flight f ON t.airline_name = f.airline_name AND t.flight_num = f.flight_num
            WHERE p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
            GROUP BY sale_type
        """)
        last_year_revenue = cursor.fetchall()

    except Error as e:
        logging.error(f"Database error occurred: {e}")
        flash(f"An error occurred while retrieving data. Please try again.")
        return redirect(url_for('staff_home'))
    finally:
        if 'cursor' in locals():
            cursor.close()

    # Render the results on the reports page
    return render_template('view_reports.html', 
                           tickets_sold_data=tickets_sold_data,
                           last_month_revenue=last_month_revenue,
                           last_year_revenue=last_year_revenue)

@app.route('/view_top_destinations', methods=['GET', 'POST'])
def view_top_destinations():
    if 'username' not in session or session.get('user_type') != "airline_staff":
        flash("Unauthorized access.")
        return redirect(url_for('login'))

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Top 3 most popular destinations in the last 3 months
        cursor.execute("""
            SELECT f.arrival_airport AS destination, COUNT(*) AS tickets_sold
            FROM ticket t
            JOIN purchases p ON t.ticket_id = p.ticket_id
            JOIN flight f ON t.airline_name = f.airline_name AND t.flight_num = f.flight_num
            WHERE p.purchase_date >= CURDATE() - INTERVAL 3 MONTH
            GROUP BY f.arrival_airport
            ORDER BY tickets_sold DESC
            LIMIT 3;
        """)
        top_destinations_3months = cursor.fetchall()

        # Top 3 most popular destinations in the last year
        cursor.execute("""
            SELECT f.arrival_airport AS destination, COUNT(*) AS tickets_sold
            FROM ticket t
            JOIN purchases p ON t.ticket_id = p.ticket_id
            JOIN flight f ON t.airline_name = f.airline_name AND t.flight_num = f.flight_num
            WHERE p.purchase_date >= CURDATE() - INTERVAL 1 YEAR
            GROUP BY f.arrival_airport
            ORDER BY tickets_sold DESC
            LIMIT 3;
        """)
        top_destinations_year = cursor.fetchall()

    except Error as e:
        logging.error(f"An error occurred: {e}")
        flash(f"An error occurred: {e}")
        return redirect(url_for('staff_home'))
    finally:
        cursor.close()

    return render_template('view_top_destinations.html', 
                           top_destinations_3months=top_destinations_3months,
                           top_destinations_year=top_destinations_year)

@app.route('/grant_permission', methods=['GET', 'POST'])
def grant_permission():
    if 'username' not in session or session.get('user_type') != "airline_staff":
        flash("Unauthorized access.")
        return redirect(url_for('login'))

    # Ensure that only Admins can grant permissions
    if 'Admin' not in session['roles']:
        flash("You are not authorized to grant permissions.")
        return redirect(url_for('staff_home'))

    if request.method == 'POST':
        staff_username = request.form['staff_username']
        new_permission = request.form['new_permission']  

        try:
            db = get_db()
            cursor = db.cursor()

            # Check if the staff exists in the airline_staff table
            cursor.execute("SELECT * FROM airline_staff WHERE username = %s", (staff_username,))
            staff = cursor.fetchone()

            if staff:
                # Check if the permission already exists for this user
                cursor.execute("""
                    SELECT * FROM permission WHERE username = %s
                """, (staff_username,))
                permission_record = cursor.fetchone()

                if permission_record:
                    # If permission already exists, update it
                    cursor.execute("""
                        UPDATE permission 
                        SET permission = %s 
                        WHERE username = %s
                    """, (new_permission, staff_username))
                else:
                    # If permission does not exist, insert a new record
                    permission_id = str(uuid.uuid4())  # Create a unique permission_id
                    cursor.execute("""
                        INSERT INTO permission (permission_id, username, permission) 
                        VALUES (%s, %s, %s)
                    """, (permission_id, staff_username, new_permission))

                db.commit()
                flash(f"Permission for {staff_username} has been updated to {new_permission}.")
            else:
                flash(f"Staff with username {staff_username} not found.")

            # Consume any remaining results from the previous query
            cursor.fetchall()  # Consume any result set, even if it's not needed

        except Error as e:
            logging.error(f"Database error occurred: {e}")
            flash(f"An error occurred while updating permission.")
        finally:
            if cursor:
                cursor.fetchall()
                cursor.close()

    return render_template('grant_permission.html')


@app.route('/add_booking_agent', methods=['GET', 'POST'])
def add_booking_agent():
    if 'username' not in session or session.get('user_type') != "airline_staff":
        flash("Unauthorized access.")
        return redirect(url_for('login'))

    # Ensure that only Admins can add booking agents
    if 'Admin' not in session['roles']:
        flash("You are not authorized to add booking agents.")
        return redirect(url_for('staff_home'))

    if request.method == 'POST':
        # Get the form data for the booking agent
        agent_email = request.form['email']
        agent_password = request.form['password']
        airline_name = session.get('airline') 
        agent_id = request.form['booking_agent_id']  # Get the integer ID from the form

        # Validate the booking_agent_id (ensure it's an integer)
        try:
            agent_id = int(agent_id)  # Ensure it's an integer
        except ValueError:
            flash("Invalid booking agent ID. It must be an integer.")
            return redirect(url_for('add_booking_agent'))

        try:
            db = get_db()
            cursor = db.cursor()

            # Check if the email already exists for a booking agent
            cursor.execute("SELECT * FROM booking_agent WHERE email = %s", (agent_email,))
            existing_agent = cursor.fetchone()

            if existing_agent:
                flash(f"A booking agent with email {agent_email} already exists.")
            else:
                # Insert new booking agent into the booking_agent table
                cursor.execute("""
                    INSERT INTO booking_agent (booking_agent_id, email, password, airline)
                    VALUES (%s, %s, %s, %s)
                """, (agent_id, agent_email, agent_password, airline_name))

                db.commit()
                flash(f"Booking agent with email {agent_email} and ID {agent_id} has been added to your airline.")

            cursor.close()

        except Error as e:
            logging.error(f"Database error occurred: {e}")
            flash(f"An error occurred while adding the booking agent.")
        
    return render_template('add_booking_agent.html')



if __name__ == '__main__':
    app.run(debug=True)