import pymysql
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import re
import os
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from flask import send_file
from werkzeug.utils import secure_filename

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
            
            # Set last login and message check time
            session['last_login'] = account.get('last_seen', datetime.now())
            session['last_checked_messages'] = account.get('last_checked_messages', datetime.now())

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
        server.set_debuglevel(1) 
        server.login('jasonbssk@gmail.com', 'mbadyjlgosqwtkrw')
        
        subject = "Your Password"
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

@app.route('/teacherindex')
def teacherindex():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute('SELECT file_name, folder, semester, course FROM files')
    files = cursor.fetchall()
    
    cursor.execute('SELECT Username FROM data WHERE Role = %s', ('student',))
    students = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('teacherindex.html', files=files, students=students)


@app.route('/upload_and_send_file', methods=['POST'])
def upload_and_send_file():
    if 'username' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))

    file = request.files['file']
    file_name = request.form['file_name']
    student_username = request.form['student_username']

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT Email FROM data WHERE Username = %s", (student_username,))
    student = cursor.fetchone()

    if not student or not student['Email']:
        flash('Student not found or email is missing.', 'danger')
        return redirect(url_for('teacherindex'))

    if file and file.filename.endswith('.pdf'):
        filename = secure_filename(file_name + ".pdf")
        file_path = os.path.join('static', 'uploads', filename)
        file.save(file_path)

        try:
            send_marked_file_via_email(student['Email'], file_path)
            flash('Marked file sent to student successfully!', 'success')
        except Exception as e:
            flash(f'Error sending file: {str(e)}', 'danger')

    else:
        flash('Invalid file. Only PDF files are allowed.', 'danger')

    cursor.close()
    connection.close()
    return redirect(url_for('teacherindex'))



def send_marked_file_via_email(student_email, file_path):
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login('jasonbssk@gmail.com', 'mbadyjlgosqwtkrw') 

        msg = MIMEMultipart()
        msg['From'] = 'jasonbssk@gmail.com'
        msg['To'] = student_email
        msg['Subject'] = 'Your submission has been marked'

        body = 'Your work with comments has been attached to this email.'
        msg.attach(MIMEText(body, 'plain'))

        attachment = open(file_path, 'rb')
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename= {os.path.basename(file_path)}')
        msg.attach(part)

        server.sendmail('jasonbssk@gmail.com', student_email, msg.as_string())
        server.quit()

        print('Email sent successfully')

    except Exception as e:
        raise Exception(f"Error sending email: {str(e)}")


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
            """
            SELECT sender, content, sent_at 
            FROM messages 
            WHERE (recipient = %s AND sender = %s) 
               OR (recipient = %s AND sender = %s) 
            ORDER BY sent_at ASC
            """, 
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
    student_username = session.get('username')  # Assuming the user is logged in and the username is stored in the session
    
    connection = get_db_connection()
    cursor = connection.cursor()
    
    # Fetch files for the student
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

    if request.method == 'POST':
        sender = session['username']  # The student sending the message
        recipient = request.form.get('recipient')  # Use get to handle missing field
        message_content = request.form.get('reply_content', '')
        
        if not recipient or not message_content:
            flash("Recipient or message content missing!", "danger")
            return redirect(url_for('studentmessages'))

        sent_at = datetime.now()
        
        # Insert the message into the messages table
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO messages (sender, recipient, content, sent_at) VALUES (%s, %s, %s, %s)",
            (sender, recipient, message_content, sent_at)
        )
        connection.commit()
        cursor.close()
        connection.close()

        flash("Message sent successfully!", "success")
        return redirect(url_for('view_messages', teacher=recipient))

    # Fetch the list of teachers
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT Username AS username FROM data WHERE Role = 'Teacher'")
    teachers = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template('studentmessages.html', teachers=teachers)



@app.route('/student_chat')
def student_chat():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Get the list of all teachers
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT username FROM users WHERE role = 'teacher'")
    teachers = cursor.fetchall()

    # Get the messages for the selected teacher (if any)
    selected_teacher = request.args.get('teacher')
    messages = []
    if selected_teacher:
        cursor.execute("""
            SELECT sender, content, sent_at FROM messages 
            WHERE (sender = %s AND recipient = %s) 
            OR (sender = %s AND recipient = %s) 
            ORDER BY sent_at ASC
        """, (session['username'], selected_teacher, selected_teacher, session['username']))
        messages = cursor.fetchall()
    
    cursor.close()
    connection.close()

    return render_template('student_chat.html', teachers=teachers, messages=messages, selected_teacher=selected_teacher)


@app.route('/get_messages', methods=['GET'])
def get_messages():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    teacher = request.args.get('teacher')
    student = session['username']

    if not teacher:
        return jsonify({'success': False, 'error': 'No teacher specified'}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT sender, recipient, content, sent_at
            FROM messages
            WHERE (sender = %s AND recipient = %s) 
            OR (sender = %s AND recipient = %s)
            ORDER BY sent_at ASC
        """, (student, teacher, teacher, student))
        messages = cursor.fetchall()
        
        messages_list = []
        for msg in messages:
            messages_list.append({
                'sender': msg['sender'],
                'recipient': msg['recipient'],
                'content': msg['content'],
                'sent_at': msg['sent_at'].strftime('%Y-%m-%d %H:%M:%S')
            })
        return jsonify({'success': True, 'messages': messages_list}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()


@app.route('/send_student_messages', methods=['GET', 'POST'])
def view_messages():
    if 'username' not in session:
        return redirect(url_for('login'))

    recipient = session['username']  # Teacher's username

    # Get a list of unique students who have messaged the teacher
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT DISTINCT sender FROM messages WHERE recipient = %s", (recipient,))
    students = cursor.fetchall()

    # Default to the first student if none is selected
    selected_student = request.args.get('student', students[0]['sender'] if students else None)

    # Fetch all messages exchanged between the teacher and the selected student
    cursor.execute("""
        SELECT sender, content, sent_at FROM messages 
        WHERE (recipient = %s AND sender = %s) 
        OR (recipient = %s AND sender = %s)
    """, (recipient, selected_student, selected_student, recipient))
    messages = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('messages.html', messages=messages, students=students, selected_student=selected_student)


# Route to send a reply
@app.route('/send_reply', methods=['POST'])
def send_reply():
    if 'username' not in session:
        return redirect(url_for('login'))

    sender = session['username']  # The teacher sending the reply
    recipient = request.form['recipient']  # The selected student
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
    return redirect(url_for('view_messages'))

if __name__ == '__main__':
    app.run(debug=True)
