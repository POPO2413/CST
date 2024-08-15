import pymysql
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import re
import os
from datetime import datetime

app = Flask(__name__)

app.secret_key = 'jason.123'

# MySQL configurations
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
            msg = 'Logged in successfully!'
            
            # Update the last_seen field with the current timestamp
            cursor.execute('UPDATE data SET last_seen = %s WHERE Username = %s', (datetime.now(), username))
            connection.commit()

            if role == 'admin':
                return redirect(url_for('adminindex'))
            elif role == 'student':
                return redirect(url_for('studentindex'))
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

@app.route('/teacherindex')
def teacherindex():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT file_name, folder FROM files')
    files = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('teacherindex.html', files=files)

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

@app.route('/studentindex')
def studentindex():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT file_name, folder FROM files')
    files = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('studentindex.html', files=files)

@app.route('/student_search_files', methods=['GET'])
def student_search_files():
    file_name = request.args.get('file_name', '')

    connection = get_db_connection()
    cursor = connection.cursor()

    query = "SELECT file_name, folder FROM files WHERE 1=1"
    params = []
    
    if file_name:
        query += " AND file_name LIKE %s"
        params.append(f"%{file_name}%")

    cursor.execute(query, params)
    files = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template('studentindex.html', files=files)

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
    
    if file and file.filename.endswith('.pdf'):
        file_path = os.path.join('static', 'pdfs', folder, file_name + '.pdf')
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        file.save(file_path)
        
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute('INSERT INTO files (file_name, folder) VALUES (%s, %s)', (file_name, folder))
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'file': {'file_name': file_name, 'folder': folder}})
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

@app.route('/econs')
def econs():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT file_name FROM files WHERE folder='Economics'")
    files = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('econs.html', files=files)

@app.route('/lit')
def lit():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT file_name FROM files WHERE folder='Literature'")
    files = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('lit.html', files=files)

if __name__ == '__main__':
    with app.test_request_context():
        print(app.url_map)
    app.run(debug=True)
