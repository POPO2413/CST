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
from fpdf import FPDF
from werkzeug.utils import secure_filename
import ssl

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
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        birthdate = request.form['birthdate']
        
        # Format the birthdate to match the database format
        try:
            birthdate = datetime.strptime(birthdate, '%Y-%m-%d').date()  # Adjust format as per your database
        except ValueError:
            msg = 'Invalid birthdate format!'
            return render_template('forgotpassword.html', msg=msg)

        # Query database for username and birthdate
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT Password FROM data WHERE Username = %s AND birthdate = %s', (username, birthdate))
        account = cursor.fetchone()
        
        if account:
            # If found, show the password
            msg = f'Your password is: {account["Password"]}'
        else:
            msg = 'Incorrect username or birthdate!'
        
        cursor.close()
        connection.close()

    return render_template('forgotpassword.html', msg=msg)

        

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        role = request.form['role']
        course = request.form['course']
        birthdate = request.form['birthdate']  # Capture birthdate from the form

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
        elif not username or not password or not email or not birthdate:  # Ensure birthdate is filled
            msg = 'Please fill out the form completely!'
        else:
            cursor.execute('INSERT INTO data (Username, Password, Email, Role, Course, Birthdate) VALUES (%s, %s, %s, %s, %s, %s)', 
                           (username, password, email, role, course, birthdate))  # Insert birthdate
            connection.commit()
            msg = 'You have successfully registered!'

        cursor.close()
        connection.close()

    return render_template('register.html', msg=msg)



@app.route('/adminindex')
def adminindex():
    connection = get_db_connection()
    cursor = connection.cursor()

    # Include birthdate in the SELECT statement and format dates
    cursor.execute('''
        SELECT ID, Username, email, Role, 
               DATE_FORMAT(Enrolled_Date, "%Y-%m-%d") as Enrolled_Date, 
               DATE_FORMAT(birthdate, "%Y-%m-%d") as birthdate 
        FROM data
    ''')
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

@app.route('/submission_report')
def submission_report():
    if session['role'] not in ['Teacher', 'Admin']:
        flash('You do not have permission to view this page.', 'danger')
        return redirect(url_for('login'))

    connection = get_db_connection()
    cursor = connection.cursor()
    
    cursor.execute("""
        SELECT username, subject, semester, file_name, submitted_time 
        FROM submitted_files
        ORDER BY submitted_time DESC
    """)
    submissions = cursor.fetchall()

    cursor.execute("SELECT DISTINCT username FROM submitted_files")
    students = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('submission_report.html', submissions=submissions, students=students)


@app.route('/generate_submission_report', methods=['GET'])
def generate_submission_report():
    # Connect to the database
    connection = get_db_connection()
    cursor = connection.cursor()

    # Fetch submission records
    cursor.execute("""
        SELECT d.Username AS student_name, f.submitted_time, f.semester, f.filename
        FROM submitted_files f
        JOIN data d ON f.username = d.Username
        WHERE f.submitted_time IS NOT NULL
        ORDER BY f.submitted_time DESC
    """)
    submissions = cursor.fetchall()
    cursor.close()
    connection.close()

    # Create output directory for the PDF
    pdf_output_dir = "static/reports"
    if not os.path.exists(pdf_output_dir):
        os.makedirs(pdf_output_dir)

    pdf = FPDF()
    pdf.add_page()

    # Title of the report
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(200, 10, "Submission Report", 0, 1, 'C')

    # Set the table header font size
    pdf.set_font('Arial', 'B', 10)

    # Adjust column widths to ensure text fits
    pdf.cell(40, 10, 'Student Name', 1)
    pdf.cell(55, 10, 'Submitted Time', 1)
    pdf.cell(20, 10, 'Semester', 1)
    pdf.cell(75, 10, 'Filename', 1)  # Increased width to fit longer filenames
    pdf.ln()

    # Set the table body font size slightly smaller to fit content better
    pdf.set_font('Arial', '', 9)

    for submission in submissions:
        student_name = submission['student_name']
        submitted_time = submission['submitted_time'].strftime("%Y-%m-%d %H:%M:%S")
        semester = submission['semester']
        file_name = submission['filename']

        pdf.cell(40, 10, student_name, 1)
        pdf.cell(55, 10, submitted_time, 1)
        pdf.cell(20, 10, semester, 1)
        pdf.cell(75, 10, file_name, 1)  # Wider cell for filenames
        pdf.ln()

    # Save the report as a PDF file
    pdf_output_path = os.path.join(pdf_output_dir, "submission_report.pdf")
    pdf.output(pdf_output_path)

    # Return the file for download
    return send_file(pdf_output_path, as_attachment=True)




# @app.route('/teacherindex')
# def teacherindex():
#     connection = get_db_connection()
#     cursor = connection.cursor()

#     cursor.execute('SELECT file_name, folder, semester, course FROM files')
#     files = cursor.fetchall()
    
#     cursor.execute('SELECT Username FROM data WHERE Role = %s', ('student',))
#     students = cursor.fetchall()

#     cursor.close()
#     connection.close()

#     return render_template('teacherindex.html', files=files, students=students)
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

@app.route('/teacher_search_files', methods=['GET'])
def teacher_search_files():
    file_name = request.args.get('file_name', '')
    folder = request.args.get('folder', '')

    connection = get_db_connection()
    cursor = connection.cursor()

    query = "SELECT file_name, folder, semester, course FROM files WHERE 1=1"
    params = []
    
    if file_name:
        query += " AND file_name LIKE %s"
        params.append(f"%{file_name}%")
        
    if folder:
        query += " AND folder LIKE %s"
        params.append(f"%{folder}%")
    
    cursor.execute(query, params)
    files = cursor.fetchall()

    # Ensure the students list is also returned for the view
    cursor.execute('SELECT Username FROM data WHERE Role = %s', ('student',))
    students = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('teacherindex.html', files=files, students=students)


@app.route('/upload_marked_file', methods=['POST'])
def upload_marked_file():
    # if 'username' not in session or session['role'] != 'teacher':
    #     return redirect(url_for('login'))

    student_username = request.form['student_username']
    subject = request.form['subject']
    semester = request.form['semester']
    file = request.files['file']

    if file and file.filename.endswith('.pdf'):
        # filename = secure_filename(file.filename)
        # file_path = os.path.join('static', 'marked', filename)
        # os.makedirs(os.path.dirname(file_path), exist_ok=True)
        # file.save(file_path)

        # marked_time = datetime.now()
        
        # connection = get_db_connection()
        # cursor = connection.cursor()
        
        # cursor.execute("""
        #     INSERT INTO marked_files (username, file_name, subject, Semester, marked_time)
        #     VALUES (%s, %s, %s, %s, %s)
        # """, (student_username, filename, subject, semester, marked_time))
        # connection.commit()

        # cursor.close()
        # connection.close()

        # return jsonify({'success': True, 'message': 'Marked file shared successfully!'}), 200
        try:
            filename = secure_filename(file.filename)
            file_path = os.path.join('static', 'marked', filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file.save(file_path)

            marked_time = datetime.now()
            
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO marked_files (username, file_name, subject, Semester, marked_time)
                VALUES (%s, %s, %s, %s, %s)
            """, (student_username, filename, subject, semester, marked_time))
            connection.commit()

            cursor.close()
            connection.close()

            return jsonify({'success': True, 'message': 'Marked file shared successfully!'}), 200

        except Exception as e:
            print(f"Error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        return jsonify({'success': False, 'error': 'Only PDF files are allowed.'}), 400


@app.route('/messages', methods=['GET', 'POST'])
def messages():
    # Get the current logged-in user's username from the session
    username = session.get('username')

    # Connect to the database
    connection = get_db_connection()
    cursor = connection.cursor()

    # Fetch the list of students the user has communicated with
    cursor.execute("""
        SELECT DISTINCT sender AS username 
        FROM messages 
        WHERE recipient = %s
        UNION
        SELECT DISTINCT recipient AS username 
        FROM messages 
        WHERE sender = %s
    """, (username, username))
    students = cursor.fetchall()

    # Determine the selected student from the URL query parameters or default to the first student
    selected_username = request.args.get('student', students[0]['username'] if students else None)

    # Fetch messages with the selected student
    messages = []
    if selected_username:
        cursor.execute("""
            SELECT sender, content, sent_at 
            FROM messages 
            WHERE (recipient = %s AND sender = %s) 
               OR (recipient = %s AND sender = %s) 
            ORDER BY sent_at ASC
        """, (username, selected_username, selected_username, username))
        messages = cursor.fetchall()

    # Handle reply (POST) requests
    if request.method == 'POST':
        recipient = request.form['recipient']
        reply_content = request.form['reply_content']
        sent_at = datetime.now()

        # Insert the new message (reply)
        cursor.execute(
            "INSERT INTO messages (sender, recipient, content, sent_at) VALUES (%s, %s, %s, %s)",
            (username, recipient, reply_content, sent_at)
        )
        connection.commit()

        # Redirect back to the same page to avoid resubmission
        flash("Reply sent successfully!", "success")
        return redirect(url_for('messages', student=recipient))

    # Close the database connection
    cursor.close()
    connection.close()

    # Render the template, passing both students and messages to the front-end
    return render_template('messages.html', students=students, messages=messages, selected_username=selected_username)


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
    username = session['username']
    subject = request.form['subject']
    semester = request.form['semester']
    file = request.files['file']
    
    if file and file.filename.endswith('.pdf'):
        try:
            filename = secure_filename(file.filename)
            upload_folder = os.path.join('static', 'uploads', username)
            os.makedirs(upload_folder, exist_ok=True)

            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            
            submitted_time = datetime.now()
            
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO submitted_files (username, subject, semester, filename, submitted_time, file_path)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (username, subject, semester, filename, submitted_time, file_path))
            connection.commit()
            cursor.close()
            connection.close()
            
            return jsonify({'success': True, 'message': 'Homework submitted successfully!'}), 200
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        return jsonify({'success': False, 'error': 'Invalid file type. Only PDF files are allowed.'}), 400

@app.route('/marked_files')
def marked_files():

    student_username = session['username']

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT file_name, subject, Semester, marked_time 
        FROM marked_files 
        WHERE username = %s
        ORDER BY marked_time DESC
    """, (student_username,))
    
    marked_files = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template('marked_files.html', marked_files=marked_files)


@app.route('/subject_search_files/<folder>', methods=['GET'])
def subject_search_files(folder):
    file_name = request.args.get('file_name', '')
    
    connection = get_db_connection()
    cursor = connection.cursor()
    
    query = "SELECT file_name, folder, semester, course FROM files WHERE LOWER(folder) = LOWER(%s)"
    params = [folder]

    if file_name:
        query += " AND LOWER(file_name) LIKE LOWER(%s)"
        params.append(f"%{file_name}%")
        
    cursor.execute(query, params)
    files = cursor.fetchall()
    print(files)
    
    files_semester1 = [file for file in files if int(file['semester']) == 1]
    files_semester2 = [file for file in files if int(file['semester']) == 2]
    
    cursor.close()
    connection.close()
    print(query)
    print(params)
    print(files_semester1)
    print(files_semester2)

    return render_template(f'{folder.lower()}.html', files_semester1=files_semester1, files_semester2=files_semester2)

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

    connection = get_db_connection()
    cursor = connection.cursor()

    # Fetch the list of teachers
    cursor.execute("SELECT Username AS username FROM data WHERE Role = 'Teacher'")
    teachers = cursor.fetchall()

    selected_teacher = request.args.get('teacher')  # The selected teacher for chatting
    messages = []

    if request.method == 'POST':
        sender = session['username']  # The student sending the message
        recipient = request.form.get('recipient')
        message_content = request.form.get('message_content', '')

        if not recipient or not message_content:
            flash("Recipient or message content missing!", "danger")
            return redirect(url_for('studentmessages'))

        sent_at = datetime.now()

        # Insert the message into the messages table
        cursor.execute(
            "INSERT INTO messages (sender, recipient, content, sent_at) VALUES (%s, %s, %s, %s)",
            (sender, recipient, message_content, sent_at)
        )
        connection.commit()

        flash("Message sent successfully!", "success")
        return redirect(url_for('studentmessages', teacher=recipient))

    # Fetch chat history with the selected teacher
    if selected_teacher:
        cursor.execute("""
            SELECT sender, content, sent_at 
            FROM messages 
            WHERE (sender = %s AND recipient = %s) 
            OR (sender = %s AND recipient = %s)
            ORDER BY sent_at ASC
        """, (session['username'], selected_teacher, selected_teacher, session['username']))
        messages = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('studentmessages.html', teachers=teachers, selected_teacher=selected_teacher, messages=messages)




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
