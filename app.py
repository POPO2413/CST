import pymysql
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import re
import os
from datetime import datetime
import smtplib

app = Flask(__name__)

app.secret_key = 'jason.123'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'jason.123'
app.config['MYSQL_DB'] = 'CS'

def get_db_connection():
    return pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        db=app.config['MYSQL_DB'],
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM data WHERE Username = %s AND Password = %s AND Role = %s', (username, password, role))
        account = cursor.fetchone()

        if account:
            session['loggedin'] = True
            session['password'] = account['Password']
            session['username'] = account['Username']
            session['role'] = account['Role']
            session['course'] = account.get('Course')  # Assuming 'Course' column exists
            msg = 'Logged in successfully!'

            cursor.execute('UPDATE data SET last_seen = %s WHERE Username = %s', (datetime.now(), username))
            connection.commit()

            if role == 'admin':
                return redirect(url_for('adminindex'))
            elif role == 'student':
                if session['course'] == 'Basic':
                    return redirect(url_for('studentbasic'))
                elif session['course'] == 'Advanced':
                    return redirect(url_for('studentadv'))
            elif role == 'teacher':
                return redirect(url_for('teacherindex'))
        else:
            msg = 'Incorrect Username / Password!'

        cursor.close()
        connection.close()

    return render_template('login.html', msg=msg)

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/forgotpassword', methods=['GET', 'POST'])
def forgotpassword():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        
        # Get user password based on provided username and email
        user_password = get_user_password_by_username_and_email(username, email)

        if user_password:
            try:
                send_password_via_email(email, user_password)
                flash('Password has been sent to your email address.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                flash(f'Failed to send email: {str(e)}', 'danger')
        else:
            flash('Username or Email not found in our system.', 'danger')

    return render_template('forgotpassword.html')

def get_user_password_by_username_and_email(username, email):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT Password FROM data WHERE Username = %s AND Email = %s", (username, email))
        result = cursor.fetchone()
        if result:
            return result['Password']
        else:
            return None
    finally:
        cursor.close()
        connection.close()

def send_password_via_email(email, user_password):
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        
        # Replace with your own email and app-specific password (not your regular email password)
        server.login('jasonbssk@gmail.com', 'mbadyjlgosqwtkrw')

        subject = "Your Website Password"
        body = f"Your password is: {user_password}"
        message = f"Subject: {subject}\n\n{body}"

        server.sendmail('jasonbssk@gmail.com', email, message)
        server.quit()
    except Exception as e:
        raise Exception(f"Error sending email: {str(e)}")



@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        role = request.form['role']
        course = request.form['course']

        connection = get_db_connection()
        cursor = connection.cursor()
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
            cursor.execute('INSERT INTO data (Username, Password, Email, Role, Course) VALUES (%s, %s, %s, %s, %s)', 
                           (username, password, email, role, course))
            connection.commit()
            msg = 'You have successfully registered!'

        cursor.close()
        connection.close()

    elif request.method == 'POST':
        msg = 'Please fill out the form!'

    return render_template('register.html', msg=msg)

@app.route('/teacherindex')
def teacherindex():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT file_name, folder FROM files')
    files = cursor.fetchall()
    cursor.close()
    connection.close()

    data = files  # or any other relevant data

    return render_template('teacherindex.html', files=files, data=data)

@app.route('/teacher_search_files', methods=['GET'])
def teacher_search_files():
    file_name = request.args.get('file_name', '')
    folder = request.args.get('folder', '')

    connection = get_db_connection()
    cursor = connection.cursor()

    query = "SELECT file_name, folder FROM files WHERE 1=1"
    params = []

    if file_name:
        query += " AND file_name LIKE %s"
        params.append(f"%{file_name}%")

    if folder:
        query += " AND folder LIKE %s"
        params.append(f"%{folder}%")

    cursor.execute(query, params)
    files = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template('teacherindex.html', files=files)

@app.route('/studentbasic')
def studentbasic():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT file_name, folder AS subject, semester, course FROM files WHERE Course = 'Basic'")
    files = cursor.fetchall()
    cursor.close()
    connection.close()
    
    # data = files
    
    # return render_template('studentbasic.html', files=files, data=data)
    return render_template('studentbasic.html', files=files)

@app.route('/studentadv')
def studentadv():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT file_name, folder AS subject, semester, course FROM files WHERE Course IN ('Basic', 'Advanced')")
    files = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('studentadv.html', files=files)

# @app.route('/student_search_files', methods=['GET'])
# def student_search_files():
#     file_name = request.args.get('file_name', '')

#     connection = get_db_connection()
#     cursor = connection.cursor()

#     query = "SELECT file_name, folder FROM files WHERE 1=1"
#     params = []

#     if file_name:
#         query += " AND file_name LIKE %s"
#         params.append(f"%{file_name}%")

#     cursor.execute(query, params)
#     files = cursor.fetchall()
#     cursor.close()
#     connection.close()

#     return render_template('studentindex.html', files=files)

@app.route('/subject_search_files/<subject>', methods=['GET'])
def subject_search_files(subject):
    file_name = request.args.get('file_name', '')

    connection = get_db_connection()
    cursor = connection.cursor()

    query = "SELECT file_name, folder FROM files WHERE folder = %s"
    params = [subject]

    if file_name:
        query += " AND file_name LIKE %s"
        params.append(f"%{file_name}%")

    cursor.execute(query, params)
    files = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template(f'{subject.lower()}.html', files=files)

@app.route('/upload_file', methods=['POST'])
def upload_file():
    file = request.files['file']
    file_name = request.form['file_name']
    folder = request.form['folder']
    semester = request.form['semester']
    course = request.form['course']
    
    if file and file.filename.endswith('.pdf'):
        file_path = os.path.join('static', 'pdfs', folder, semester, course, file_name + '.pdf')
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        file.save(file_path)

        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute('INSERT INTO files (file_name, folder, semester, course) VALUES (%s, %s, %s, %s)', (file_name, folder, semester, course))
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'file': {'file_name': file_name, 'folder': folder, 'semester': semester, 'course': course}})
    return jsonify({'success': False, 'error': 'Only PDF files are allowed.'}), 400

@app.route('/student_upload_file', methods=['POST'])
def student_upload_file():
    file = request.files['file']
    file_name = request.form['file_name']
    folder = request.form['folder']
    semester = request.form['semester']
    course = request.form['course']
    subject = request.form['subject']
    
    if file and file.filename.endswith('.pdf'):
        file_path = os.path.join('static', 'pdfs', folder, subject, semester, course, file_name + '.pdf')
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        file.save(file_path)
        
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute('INSERT INTO files (file_name, folder, subject, semester, course) VALUES (%s, %s, %s, %s, %s)', (file_name, folder, subject, semester, course))
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'file': {'file_name': file_name, 'folder': folder, 'semester': semester, 'course': course, 'subject': subject}})
    return jsonify({'success': False, 'error': 'Only PDF files are allowed.'}), 400

@app.route('/math')
def math():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT file_name FROM files WHERE folder='Math'")
    files = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('math.html', files=files)

@app.route('/science')
def science():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT file_name FROM files WHERE folder='Science'")
    files = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('science.html', files=files)

@app.route('/economics')
def economics():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT file_name FROM files WHERE folder='Economics'")
    files = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('economics.html', files=files)

@app.route('/literature')
def literature():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT file_name FROM files WHERE folder='Literature'")
    files = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('literature.html', files=files)

@app.route('/adminindex')
def adminindex():
    connection = get_db_connection()
    cursor = connection.cursor()
    # Format Enrolled_Date to show only the date (YYYY-MM-DD)
    cursor.execute('SELECT ID, Username, email, Role, DATE_FORMAT(Enrolled_Date, "%Y-%m-%d") as Enrolled_Date FROM data')
    users = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('adminindex.html', users=users)



@app.route('/user_activity')
def user_activity():
    query = request.args.get('search', '').lower()
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT Username, modified, last_seen FROM data')
    activities = cursor.fetchall()

    if query:
        activities = [activity for activity in activities if query in activity['Username'].lower()]

    cursor.close()
    connection.close()
    return render_template('user_activity.html', activities=activities)

@app.route('/manageusers')
def manageusers():
    query = request.args.get('search', '').lower()
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT Username, email, Role FROM data')
    users = cursor.fetchall()

    if query:
        users = [user for user in users if query in user['Username'].lower()]

    cursor.close()
    connection.close()

    if request.is_json:
        return jsonify({'users': users})
    return render_template('manageusers.html', users=users)

@app.route('/managefiles', methods=['GET', 'POST'])
def managefiles():
    connection = get_db_connection()
    cursor = connection.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        file_name = request.form.get('file_name')

        if action == 'delete':
            cursor.execute("DELETE FROM files WHERE file_name = %s", (file_name,))
            connection.commit()
        elif action == 'rename':
            new_file_name = request.form.get('new_file_name')
            cursor.execute("UPDATE files SET file_name = %s WHERE file_name = %s", (new_file_name, file_name))
            connection.commit()

    cursor.execute('SELECT file_name, folder FROM files')
    files = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('managefiles.html', files=files)

@app.route('/change_role', methods=['POST'])
def change_role():
    data = request.get_json()
    new_role = data.get('role')
    user_ids = data.get('users')

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        for username in user_ids:
            cursor.execute("UPDATE data SET Role = %s WHERE Username = %s", (new_role.capitalize(), username))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'message': 'Role updated successfully'}), 200
    except Exception as e:
        connection.rollback()
        cursor.close()
        connection.close()
        return jsonify({'message': 'Failed to update role', 'error': str(e)}), 500

@app.route('/rename_file', methods=['POST'])
def rename_file():
    data = request.get_json()
    old_file_name = data.get('old_file_name')
    new_file_name = data.get('new_file_name')

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("UPDATE files SET file_name = %s WHERE file_name = %s", (new_file_name, old_file_name))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'message': 'File renamed successfully'}), 200
    except Exception as e:
        connection.rollback()
        cursor.close()
        connection.close()
        return jsonify({'message': 'Failed to rename file', 'error': str(e)}), 500

@app.route('/delete_file', methods=['POST'])
def delete_file():
    data = request.get_json()
    file_name = data.get('file_name')

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM files WHERE file_name = %s", (file_name,))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'message': 'File deleted successfully'}), 200
    except Exception as e:
        connection.rollback()
        cursor.close()
        connection.close()
        return jsonify({'message': 'Failed to delete file', 'error': str(e)}), 500

@app.route('/rename_user', methods=['POST'])
def rename_user():
    data = request.get_json()
    old_username = data.get('old_username')
    new_username = data.get('new_username')

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("UPDATE data SET Username = %s WHERE Username = %s", (new_username, old_username))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'message': 'User renamed successfully'}), 200
    except Exception as e:
        connection.rollback()
        cursor.close()
        connection.close()
        return jsonify({'message': 'Failed to rename user', 'error': str(e)}), 500

@app.route('/delete_user', methods=['POST'])
def delete_user():
    data = request.get_json()
    username = data.get('username')

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM data WHERE Username = %s", (username,))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'message': 'User deleted successfully'}), 200
    except Exception as e:
        connection.rollback()
        cursor.close()
        connection.close()
        return jsonify({'message': 'Failed to delete user', 'error': str(e)}), 500


if __name__ == '__main__':
    with app.test_request_context():
        print(app.url_map)
    app.run(debug=True)
