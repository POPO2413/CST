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
app.config['MYSQL_DB'] = 'Compsci_Data'

mysql = MySQL(app)

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM data WHERE Username = %s AND Password = %s AND Role = %s', (username, password, role))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['password'] = account['Password']
            session['username'] = account['Username']
            session['role'] = account['Role']
            msg = 'Logged in successfully !'
            print(role)
   
            if role == 'admin':
                return redirect(url_for('adminindex'))
            elif role == 'student':
                return redirect(url_for('studentindex'))
            elif role == 'teacher':
                return redirect(url_for('teacherindex'))
            
            ########### Debugging ###########
            else:
                msg = 'Incorrect Username / Password!'
                print(f"Failed login attempt for {username} with role {role}")
            
        else:
            msg = 'Incorrect Username / Password !'
    return render_template('login.html', msg=msg)

@app.route('/adminindex')
def adminindex():
    return render_template('adminindex.html')

@app.route('/studentindex')
def studentindex():
    if 'loggedin' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    return render_template('studentindex.html')

@app.route('/teacherindex')
def teacherindex():
    if 'loggedin' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    return render_template('teacherindex.html')

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('Username', None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'Username' in request.form and 'Password' in request.form and 'Email' in request.form:
        username = request.form['Username']
        password = request.form['Password']
        email = request.form['Email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM data WHERE Username = %s', (username,))
        account = cursor.fetchone()
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            cursor.execute('INSERT INTO data VALUES (NULL, %s, %s, %s)', (username, password, email,))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
    elif request.method == 'POST':
        msg = 'Please fill out the form!'
    return render_template('register.html', msg=msg)

@app.route('/query_data', methods=['GET'])
def query_data():
    return render_template('query_data.html')

@app.route('/search_data', methods=['GET'])
def search_data():
    query = request.args.get('query')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM data WHERE Username LIKE %s", ('%' + query + '%',))
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

@app.route('/manageroles', endpoint='manageroles')
def manageroles():
    return render_template('manageroles.html')

if __name__ == '__main__':
    with app.test_request_context():
        print(app.url_map)
    app.run(debug=True)

    
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/users')
def users():
    return render_template('users.html')

@app.route('/activities')
def activities():
    return render_template('activities.html')

@app.route('/manage_users')
def manage_users():
    return render_template('manage_users.html')

@app.route('/manage_files')
def manage_files():
    return render_template('manage_files.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/api/users', methods=['GET'])
def api_users():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT Username, Email FROM users')
    users = cursor.fetchall()
    return {"users": users}

