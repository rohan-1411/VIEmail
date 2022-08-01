from flask import *
import pymysql
import smtplib
import imaplib
import email
import json
from email.mime.text import MIMEText
from passlib.hash import sha256_crypt

connection = pymysql.connect(host="localhost",user="root",passwd="",database="vi_email")
cursor = connection.cursor()

# connect with Google's servers
smtp_ssl_host = 'smtp.gmail.com'
smtp_ssl_port = 465
imap_host = 'imap.gmail.com'

app = Flask(__name__) # Flask Object
app.secret_key = "abc"
@app.route('/', methods=["POST","GET"])
def index():
    try:
        choice = request.args['choice'].strip()
    except:
        choice = 0
    return render_template('index.html', title="Welcome to VI-EMAIL", choice=choice)

@app.route('/service-worker.js')
def sw():
    return app.send_static_file('service-worker.js')

@app.route('/loginPage', methods=['POST', 'GET'])
def loginPage():
    return render_template('login.html', title="VIEmail - Login", choice='1')

@app.route('/registerPage', methods=['POST', 'GET'])
def registerPage():
    return render_template('register.html', title="VIEmail - Register")

@app.route('/checkLogin', methods=['POST'])
def checkLogin():
    if request.method == 'POST':
        entered_email = request.form['user_email'].strip()
        entered_password = request.form['user_password'].strip()

        sqlQuery = "SELECT `email`, `password` FROM `users`"
        cursor.execute(sqlQuery)
        result = cursor.fetchall()
        for row in result:
            email = row[0]
            psw = row[1]
            if entered_email == email and sha256_crypt.verify(entered_password,psw):
                session['user'] = entered_email
                session['password'] = entered_password
                return redirect(url_for('main', choice='1'))

    return render_template('login.html', choice='2')

@app.route('/registerUser', methods=['POST', 'GET'])
def registerUser():
    entered_user = request.form['user_name'].strip()
    entered_email = request.form['user_email'].strip()
    entered_password = request.form['user_password'].strip()
    compareQuery = "SELECT `email` FROM `users`"
    cursor.execute(compareQuery)
    res = cursor.fetchall()
    for row in res:
        a = row[0]
        if a == entered_email:
            return "<script> alert('Same Data Present') </script>"

    sqlQuery = "INSERT INTO `users` VALUES('{0}','{1}','{2}')".format(entered_user, entered_email, sha256_crypt.hash(entered_password))
    cursor.execute(sqlQuery)
    connection.commit()
    return render_template('main.html', choice='3')

@app.route('/main')
def main():
    try:
        choice = request.args['choice'].strip()
    except:
        choice = 0
    return render_template('main.html', title="VIEmail - Home", choice=choice)

@app.route('/sendPage', methods=['POST', 'GET'])
def sendPage():
    return render_template('send.html', title="VIEmail - Send Email")

@app.route('/sendEmail', methods=['POST', 'GET'])
def sendEmail():
    userEmail = session['user']
    userPass = session['password']

    sqlQuery = "SELECT `email`, `password` FROM `users`"
    cursor.execute(sqlQuery)
    result = cursor.fetchall()
    for row in result:
        email = row[0]
        psw = row[1]
        if userEmail == email:
            userPass += psw
            break

    from_addr = userEmail
    to_addrs = request.form['recipient'].strip()
    subject = request.form['subject'].strip()
    emailMessage = request.form['message'].strip()

    message = MIMEText(emailMessage)
    message['subject'] = subject
    message['from'] = from_addr
    message['to'] = to_addrs

    server = smtplib.SMTP_SSL(smtp_ssl_host, smtp_ssl_port)
    server.login(userEmail, userPass)
    server.sendmail(from_addr, to_addrs, message.as_string())
    server.quit()
    return '1'

@app.route('/viewPage', methods=['POST', 'GET'])
def viewPage():
    return render_template('view.html', title="VIEmail - View Email")

@app.route('/viewEmail', methods=['POST', 'GET'])
def viewEmail():
    imap_user = session['user']
    imap_pass = session['password']
    from_email = request.form['user'].strip()
    try:
        imap = imaplib.IMAP4_SSL(imap_host)
        imap.login(imap_user, imap_pass)

        imap.select('Inbox')
        result, data = imap.search(None, '(FROM "{}")'.format(from_email))
        inbox_item_list = data[0].split()
        new = inbox_item_list[-1]
        result2, email_data = imap.uid('fetch', new, '(RFC822)')  # fetch

        raw_email = email_data[0][1].decode("utf-8")  # decode
        email_message = email.message_from_string(raw_email)

        _, msg = imap.fetch(new, '(RFC822)')
        txt = ""
        message = email.message_from_bytes(msg[0][1])
        multipart_payload = message.get_payload()
        for sub_message in multipart_payload:
            # The actual text/HTML email contents, or attachment data
            content_type = sub_message.get_content_type()
            if content_type == "text/plain":
                txt = sub_message.get_payload()

        res = {
            "from": str(email_message['From']),
            "subject": str(email_message['Subject']),
            "message": txt
        }
    except:
        res = {"from": '0'}

    return json.dumps(res)

@app.route('/logout', methods=["POST","GET"])
def logout():
    try:
        session.pop('user', None)
        session.pop('password', None)
        return "10"
    except:
        return "0"

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)