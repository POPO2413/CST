# Store this code in 'app.py' file

from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import os


app = Flask(__name__)


app.secret_key = 'jason.123'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'jason.123'
app.config['MYSQL_DB'] = 'geeklogin'

mysql = MySQL(app)

@app.route('/')
@app.route('/login', methods =['GET', 'POST'])
def login():
	msg = ''
	if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
		username = request.form['username']
		password = request.form['password']
		role = request.form['role']
		cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute('SELECT * FROM Data WHERE Name = %s AND password = %s AND Role = %s', (username, password,role))
		account = cursor.fetchone()
		if account:
			session['loggedin'] = True
			session['password'] = account['Password']
			session['username'] = account['Name']
			session['role'] = account['Role']
			msg = 'Logged in successfully !'
			# return render_template('index.html', msg = msg)
			print(role)
   
			if role == 'admin':
				return redirect(url_for('adminindex'))
			elif role == 'student':
				return redirect(url_for('student_index'))
			elif role == 'teacher':
				return redirect(url_for('teacher_index'))
		else:
			msg = 'Incorrect username / password !'
	return render_template('login.html', msg = msg)

@app.route('/adminindex')
def adminindex():
    # if session['role'] != 'Admin':
    #     print("back to login")
    #     return redirect(url_for('login'))
    # print("to admin page")
    return render_template('adminindex.html')

@app.route('/student_index')
def student_index():
    if 'loggedin' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    return render_template('student_index.html')

@app.route('/teacher_index')
def teacher_index():
    if 'loggedin' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    return render_template('teacher_index.html')

@app.route('/logout')
def logout():
	session.pop('loggedin', None)
	session.pop('id', None)
	session.pop('username', None)
	return redirect(url_for('login'))

@app.route('/register', methods =['GET', 'POST'])
def register():
	msg = ''
	if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form :
		username = request.form['username']
		password = request.form['password']
		email = request.form['email']
		cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute('SELECT * FROM accounts WHERE username = % s', (username, ))
		account = cursor.fetchone()
		if account:
			msg = 'Account already exists !'
		elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
			msg = 'Invalid email address !'
		elif not re.match(r'[A-Za-z0-9]+', username):
			msg = 'Username must contain only characters and numbers !'
		elif not username or not password or not email:
			msg = 'Please fill out the form !'
		else:
			cursor.execute('INSERT INTO accounts VALUES (NULL, % s, % s, % s)', (username, password, email, ))
			mysql.connection.commit()
			msg = 'You have successfully registered !'
	elif request.method == 'POST':
		msg = 'Please fill out the form !'
	return render_template('register.html', msg = msg)

@app.route('/query_data', methods=['GET'])
def query_data():
	return render_template('query_data.html')

@app.route('/search_data', methods=['GET'])
def search_data():
    query = request.args.get('query')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM your_table_name WHERE student_name LIKE %s", ('%' + query + '%',))
    search_results = cursor.fetchall()
    return render_template('query_data.html', search_results=search_results)


@app.route('/search_files', methods=['GET'])
def search_files():
    query = request.args.get('filename', '')
    search_directory = './files'  # Adjust the path to where your files are stored
    matching_files = []

    # Search for matching files in the directory
    for root, dirs, files in os.walk(search_directory):
        for filename in files:
            if query.lower() in filename.lower():
                matching_files.append(os.path.join(root, filename))

    if matching_files:
        results = '<br>'.join(matching_files)
    else:
        results = "No files found."

    return f"Results for '{query}':<br>{results}"

if __name__ == '__main__':
    app.run(debug=True)
 


from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2  # or any other database connection library


@app.route('/manageroles', methods=['GET', 'POST'])
def manageroles():
    if 'username' in session:
        # Assuming you have database setup to connect and fetch data
        connection = psycopg2.connect(user="your_user",
                                      password="your_password",
                                      host="127.0.0.1",
                                      port="5432",
                                      database="your_database")
        cursor = connection.cursor()

        # Fetch users and their roles
        cursor.execute("SELECT username, role FROM users")  # Adjust SQL based on your schema
        user_roles = cursor.fetchall()
        cursor.close()
        connection.close()

        return render_template('manageroles.html', user_roles=user_roles)
    else:
        return redirect(url_for('login'))
	
if __name__ == '__main__':
    app.run(debug=True)

# Ensure you have methods to handle login and index routes as well







	