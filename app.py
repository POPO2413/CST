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
            
            if role == 'student':
                session['course'] = account.get('Course')
            else:
                session['course'] = None
            
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
        server.login('jasonbssk@gmail.com', 'mbadyjlgosqwtkrw')

        subject = "Your Website Password"
        body = f"Your password is: {user_password}"
        message = f"Subject: {subject}\n\n{body}"

        server.sendmail('annieeeee2203@gmail.com', email, message)
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

    return render_template('register.html', msg=msg)


@app.route('/adminindex')
def adminindex():
    connection = get_db_connection()
    cursor = connection.cursor()
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

@app.route('/teacherindex')
def teacherindex():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT file_name, folder, semester, course FROM files')
    files = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template('teacherindex.html', files=files)

@app.route('/messages', methods=['GET', 'POST'])
def messages():
    teacher_username = session.get('username')  # Get the teacher's username from the session

    connection = get_db_connection()
    cursor = connection.cursor()

    # Fetch the list of unique students who have messaged the teacher
    cursor.execute("SELECT DISTINCT sender FROM messages WHERE recipient = %s", (teacher_username,))
    students = cursor.fetchall()

    # Default to the first student if none is selected
    selected_student = request.args.get('student', students[0]['sender'] if students else None)
    messages = []

    if selected_student:
        # Fetch all messages exchanged between the teacher and the selected student
        cursor.execute(
            "SELECT sender, content, sent_at FROM messages WHERE (recipient = %s AND sender = %s) OR (recipient = %s AND sender = %s) ORDER BY sent_at ASC",
            (teacher_username, selected_student, selected_student, teacher_username)
        )
        messages = cursor.fetchall()

    if request.method == 'POST':
        # Teacher sends a reply
        recipient = request.form['recipient']
        reply_content = request.form['reply_content']
        sent_at = datetime.now()

        # Insert the reply into the messages table
        cursor.execute(
            "INSERT INTO messages (sender, recipient, content, sent_at) VALUES (%s, %s, %s, %s)",
            (teacher_username, recipient, reply_content, sent_at)
        )
        connection.commit()

        flash("Reply sent successfully!", "success")
        return redirect(url_for('messages', student=recipient))

    cursor.close()
    connection.close()

    return render_template('messages.html', students=students, messages=messages, selected_student=selected_student)




@app.route('/studentbasic')
def studentbasic():
    connection = get_db_connection()
    cursor = connection.cursor()

    # Fetch files for the student
    cursor.execute("SELECT file_name, folder AS subject, semester, course FROM files WHERE Course = 'Basic'")
    files = cursor.fetchall()

    # Fetch the list of teachers
    cursor.execute("SELECT Username FROM data WHERE Role = 'Teacher'")
    teachers = cursor.fetchall()

    cursor.close()
    connection.close()
    
    return render_template('studentbasic.html', files=files, teachers=teachers)


@app.route('/studentadv')
def studentadv():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT file_name, folder AS subject, semester, course FROM files WHERE Course IN ('Basic', 'Advanced')")
    files = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('studentadv.html', files=files)

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
    
    # files for Semester 1
    cursor.execute("SELECT file_name FROM files WHERE folder='Math' AND semester=1")
    files_semester1 = cursor.fetchall()
    
    # files for Semester 2
    cursor.execute("SELECT file_name FROM files WHERE folder='Math' AND semester=2")
    files_semester2 = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    return render_template('math.html', files_semester1=files_semester1, files_semester2=files_semester2)

@app.route('/science')
def science():
    connection = get_db_connection()
    cursor = connection.cursor()

    # files for Semester 1 
    cursor.execute("SELECT file_name FROM files WHERE folder='Science' AND semester=1")
    files_semester1 = cursor.fetchall()
    
    # files for Semester 2 
    cursor.execute("SELECT file_name FROM files WHERE folder='Science' AND semester=2")
    files_semester2 = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('science.html', files_semester1=files_semester1, files_semester2=files_semester2)

@app.route('/economics')
def economics():
    connection = get_db_connection()
    cursor = connection.cursor()

    # files for Semester 1
    cursor.execute("SELECT file_name FROM files WHERE folder='Economics' AND semester=1")
    files_semester1 = cursor.fetchall()

    # files for Semester 2
    cursor.execute("SELECT file_name FROM files WHERE folder='Economics' AND semester=2")
    files_semester2 = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('economics.html', files_semester1=files_semester1, files_semester2=files_semester2)


@app.route('/literature')
def literature():
    connection = get_db_connection()
    cursor = connection.cursor()

    # files for Semester 1
    cursor.execute("SELECT file_name FROM files WHERE folder='Literature' AND semester=1")
    files_semester1 = cursor.fetchall()

    # files for Semester 2
    cursor.execute("SELECT file_name FROM files WHERE folder='Literature' AND semester=2")
    files_semester2 = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('literature.html', files_semester1=files_semester1, files_semester2=files_semester2)


@app.route('/studentmessages', methods=['GET', 'POST'])
def studentmessages():
    if 'username' not in session:
        return redirect(url_for('login'))

    student_username = session['username']

    connection = get_db_connection()
    cursor = connection.cursor()

    # Fetch the list of teachers
    cursor.execute("SELECT Username AS username FROM data WHERE Role = 'Teacher'")
    teachers = cursor.fetchall()

    if request.method == 'POST':
        # Handle the form submission
        recipient = request.form['recipient']  # The teacher's username (recipient)
        message_content = request.form['message_content']
        sent_at = datetime.now()

        # Insert the new message into the database
        cursor.execute(
            "INSERT INTO messages (sender, recipient, content, sent_at) VALUES (%s, %s, %s, %s)",
            (student_username, recipient, message_content, sent_at)
        )
        connection.commit()

        # After inserting, reload the conversation with the selected teacher
        flash("Message sent successfully!", "success")
        return redirect(url_for('studentmessages', teacher=recipient))

    # If it's a GET request, show the conversation with the selected teacher
    selected_teacher = request.args.get('teacher')
    messages = []

    if selected_teacher:
        # Fetch messages between the student and the selected teacher
        cursor.execute(
            "SELECT sender, content, sent_at FROM messages WHERE (sender = %s AND recipient = %s) OR (sender = %s AND recipient = %s) ORDER BY sent_at ASC",
            (student_username, selected_teacher, selected_teacher, student_username)
        )
        messages = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('studentmessages.html', teachers=teachers, messages=messages, selected_teacher=selected_teacher)


@app.route('/send_reply', methods=['POST'])
def send_reply():
    if 'username' not in session:
        return redirect(url_for('login'))

    sender = session['username']  # The teacher is sending the reply
    recipient = request.form['recipient']  # Get the recipient from the form
    reply_content = request.form['reply_content']
    sent_at = datetime.now()

    # Insert the reply into the messages table
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO messages (sender, recipient, content, sent_at) VALUES (%s, %s, %s, %s)",
        (sender, recipient, reply_content, sent_at)
    )
    connection.commit()
    cursor.close()
    connection.close()

    flash("Reply sent successfully!", "success")
    return redirect(url_for('messages'))

if __name__ == '__main__':
    app.run(debug=True)
