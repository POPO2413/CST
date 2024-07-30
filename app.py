from flask import Flask, render_template, request, redirect, url_for, session, jsonify
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
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT Username, email, Role FROM data')
    users = cursor.fetchall()
    return render_template('adminindex.html', users=users)

@app.route('/user_activity')
def user_activity():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT Username, modified, last_seen FROM data')
    activities = cursor.fetchall()
    return render_template('user_activity.html', activities=activities)

@app.route('/manageusers')
def manageusers():
    query = request.args.get('search', '')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if query:
        cursor.execute('SELECT Username, email, Role FROM data WHERE Username LIKE %s', 
                       ('%' + query + '%',))
    else:
        cursor.execute('SELECT Username, email, Role FROM data')
    users = cursor.fetchall()
    
    if request.is_json:
        return jsonify({'users': users})
    return render_template('manageusers.html', users=users)

@app.route('/change_role', methods=['POST'])
def change_role():
    data = request.get_json()
    new_role = data.get('role')
    user_ids = data.get('users')

    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        for username in user_ids:
            cursor.execute("UPDATE data SET Role = %s WHERE Username = %s", (new_role, username))
        mysql.connection.commit()
        return jsonify({'message': 'Role updated successfully'}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'message': 'Failed to update role', 'error': str(e)}), 500

# @app.route('/change_role/<username>', methods=['POST'])
# def change_role(username):
#     new_role = request.form['new_role']
#     cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
#     cursor.execute("UPDATE Data SET Role = %s WHERE Username = %s", (new_role, username))
#     mysql.connection.commit()
#     return redirect(url_for('manageusers'))

@app.route('/managefiles')
def managefiles():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT file_name, folder FROM files')
    files = cursor.fetchall()
    return render_template('managefiles.html', files=files)

@app.route('/rename_file', methods=['POST'])
def rename_file():
    data = request.get_json()
    old_file_name = data.get('old_file_name')
    new_file_name = data.get('new_file_name')

    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("UPDATE files SET file_name = %s WHERE file_name = %s", (new_file_name, old_file_name))
        mysql.connection.commit()
        return jsonify({'message': 'File renamed successfully'}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'message': 'Failed to rename file', 'error': str(e)}), 500

@app.route('/delete_file', methods=['POST'])
def delete_file():
    data = request.get_json()
    file_name = data.get('file_name')

    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("DELETE FROM files WHERE file_name = %s", (file_name,))
        mysql.connection.commit()
        return jsonify({'message': 'File deleted successfully'}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'message': 'Failed to delete file', 'error': str(e)}), 500


# @app.route('/user_activity', methods=['GET'])
# def user_activity():
#     query = request.args.get('query')
#     cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
#     if query:
#         cursor.execute("SELECT * FROM Data WHERE Username LIKE %s", ('%' + query + '%',))
#     else:
#         cursor.execute("SELECT * FROM Data")
#     users = cursor.fetchall()
#     return render_template('user_activity.html', users=users, query=query)

# @app.route('/managefiles')
# def managefiles():
#     cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
#     # change the SQL query accordingly
#     cursor.execute('SELECT filename, folder FROM files') 
#     files = cursor.fetchall()
#     return render_template('managefiles.html', files=files)


# @app.route('/manageusers')
# def manageusers():
#     return render_template('manageusers.html')


@app.route('/studentindex')
def studentindex():

    return render_template('studentindex.html')

@app.route('/teacherindex')
def teacherindex():
    if 'loggedin' not in session or session['role'] != 'Teacher':
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


@app.route('/api/users', methods=['GET'])
def api_users():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT Username, Email FROM users')
    users = cursor.fetchall()
    return {"users": users}

# Routes for each subject
@app.route('/math')
def math():
    return render_template('math.html')

@app.route('/science')
def science():
    return render_template('science.html')

@app.route('/econs')
def econs():
    return render_template('econs.html')

@app.route('/lit')
def lit():
    return render_template('lit.html')



if __name__ == '__main__':
    with app.test_request_context():
        print(app.url_map)
    app.run(debug=True)


# if __name__ == '__main__':
#     app.run(debug=True)
