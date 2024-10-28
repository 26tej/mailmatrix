from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector  # Used to connect to the MySQL RDS instance
import boto3  # AWS SDK for Python
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace this with a secure random key for production

# Initialize the Boto3 Lambda client
lambda_client = boto3.client('lambda', region_name='ap-south-1')  # Set AWS region

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/govexamlist')
def govexamlist():
    return render_template('govexamlist.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')
        email = request.form.get('email')
        qualification = request.form.get('qualification')
        exam = request.form.get('exam')

        # Check if any field is empty
        if not all([name, age, email, qualification, exam]):
            flash('All fields are required!', 'error')
            return redirect(url_for('register'))

        # Connect to the MySQL database
        try:
            conn = mysql.connector.connect(
                host='database-1.cnqokwycqp5w.ap-south-1.rds.amazonaws.com',  # Replace with your RDS endpoint
                user='admin',  # Replace with your RDS username
                password='Admin123',  # Replace with your RDS password
                database='MailMatrix'  # Replace with your database name
            )
            cursor = conn.cursor()
            # Insert registration details into the database
            cursor.execute(
                "INSERT INTO registrations (name, age, email, qualification, exam) VALUES (%s, %s, %s, %s, %s)",
                (name, age, email, qualification, exam)
            )
            conn.commit()
            flash('Registration successful!', 'success')
        except mysql.connector.Error as e:
            print(f'Database error: {str(e)}')
            flash(f'Database error: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')

@app.route('/send_exam_notifications', methods=['POST'])
def send_exam_notifications():
    """Trigger AWS Lambda to send exam notifications in bulk."""
    students = []
    
    try:
        # Connect to the MySQL database
        conn = mysql.connector.connect(
            host='database-1.cnqokwycqp5w.ap-south-1.rds.amazonaws.com',
            user='admin',
            password='Admin123',
            database='MailMatrix'
        )
        cursor = conn.cursor(dictionary=True)

        # Retrieve registered students from the database
        cursor.execute("SELECT name, email, exam FROM registrations")
        students = cursor.fetchall()  # List of dictionaries with 'name', 'email', 'exam'

    except mysql.connector.Error as e:
        print(f'Database error: {str(e)}')
        flash(f'Database error: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        cursor.close()
        conn.close()

    # Check if students data was retrieved
    if not students:
        flash('No students registered to send notifications.', 'error')
        return redirect(url_for('index'))

    try:
        # Invoke the Lambda function with the students payload
        response = lambda_client.invoke(
            FunctionName='SendExamNotifications',  # Replace with your Lambda function name
            InvocationType='Event',  # Asynchronous invocation
            Payload=json.dumps({"students": students})
        )

        # Check the response status code
        if response['StatusCode'] == 202:
            flash('Exam notifications have been sent successfully!', 'success')
        else:
            flash(f'Failed to send notifications. Status code: {response["StatusCode"]}', 'error')

    except Exception as e:
        flash(f'Error sending notifications: {str(e)}', 'error')
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
