from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import mysql.connector


app = Flask(
    # 將靜態檔案放到前端
    __name__,
    static_folder="public",  # 靜態檔案如文字檔、圖檔、CSS檔放在public將檔案送到前端
    static_url_path="/public"
)
app.secret_key = "any string but secret"  # 設定session

# 自己資料庫的訊息，定義一次即可
config = {
    'user': 'root',
    'password': 'root',
    'host': '',
    'database': 'website',
    'raise_on_warnings': True
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/signin", methods=["POST"])
def signin():
    username = request.form['account2']
    password = request.form['password2']

    # 建立資料庫連結並查詢
    connection = mysql.connector.connect(**config)  # 連至資料庫
    cursor = connection.cursor(buffered=True)  # 執行查詢

    cursor.execute(
        "SELECT id, name, password FROM member WHERE username = %s", (username,))  # 用(username,)去尋找前面要求的username以及password資訊
    user_data = cursor.fetchone()
    cursor.close()
    connection.close()

    # 不要直接核對帳號，因為若無資料，整筆料會回傳None。這時使用帳號索引核對，會產生typeerror
    if user_data and user_data[2] == password:
        session["user_id"] = user_data[0]
        session["username"] = username
        session["name"] = user_data[1]
        return redirect('/member')
    else:
        error_message = '帳號或密碼錯誤'
        return redirect(url_for('error', message=error_message))


@app.route("/signup", methods=["POST"])
def signup():
    name = request.form.get('name1')
    username = request.form.get('account1')
    password = request.form.get('password1')
    connection = mysql.connector.connect(**config)
    cursor = connection.cursor(buffered=True)

    cursor.execute(
        "SELECT username FROM member WHERE username = %s", (username,))
    account = cursor.fetchone()
    cursor.close()
    connection.close()

    if account:  # 若account有回傳資訊，則帶彆被註冊
        error_message = '帳號已經被註冊'
        return redirect(url_for('error', message=error_message))
    else:
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor(buffered=True)
        cursor.execute(
            "INSERT INTO member(name,username,password) VALUES (%s,%s,%s) ", (name, username, password))
        connection.commit()  # 永久儲存資料
        cursor.close()
        connection.close()
        return redirect("/")


@app.route("/member")
def member():
    if "username" in session:
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor(buffered=True)
        cursor.execute(
            "SELECT member.name, message.content, message.id FROM message JOIN member ON message.member_id = member.id ORDER BY message.id DESC")
        messages = cursor.fetchall()
        cursor.close()
        connection.close()

        # name要放在登入成功頁面進行互動
        return render_template('success.html', name=session["name"], messages=messages)
    else:
        return redirect("/")


@app.route("/error")
def error():
    error_message = request.args.get("message")
    return render_template('error.html', error_message=error_message)


@app.route("/signout")
def signout():
    keys = ["user_id", "username", "name"]
    for key in keys:
        session.pop(key, None)  # None是默認值，避免異常狀態跳出
    return redirect("/")


@app.route("/createMessage", methods=["POST"])
def createMessage():
    if "username" in session:
        content = request.form.get("message")
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        cursor.execute("INSERT INTO message (member_id, content) VALUES (%s, %s)",
                       (session["user_id"], content))
        connection.commit()
        cursor.close()
        connection.close()
        return redirect("/member")


@app.route("/deleteMessage", methods=["POST"])
def deleteMessage():
    data = request.json
    message_id = data['id']
    connection = mysql.connector.connect(**config)
    cursor = connection.cursor()
    cursor.execute("DELETE FROM message WHERE id = %s", (message_id,))
    connection.commit()
    cursor.close()
    connection.close()
    return '', 200


@app.route("/api/member", methods=['GET', 'PATCH'])
def find_member():
    if request.method == 'GET':
        username = request.args.get('username')
        if not username or username.strip() == "" or "username" not in session:
            return jsonify(data=None)
        try:
            connection = mysql.connector.connect(**config)
            cursor = connection.cursor(dictionary=True)  # 设置为字典模式，使结果以字典形式返回
            cursor.execute(
                "SELECT * FROM member WHERE username = %s", (username,))
            member = cursor.fetchone()

            if member:
                response_data = {
                    "data": {
                        "id": member["id"],
                        "name": member["name"],
                        "username": member["username"]}
                }
            else:
                response_data = {
                    "data": None
                }
            return jsonify(response_data)
        except Exception as e:  # 這邊捕捉到任何異常都回應查無資料
            print(e)
            return jsonify(data=None)

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    elif request.method == 'PATCH':
        if "username" not in session:
            return jsonify(error=True)
        new_name = request.json.get('name')
        if not new_name:
            return jsonify(error=True)
        try:
            connection = mysql.connector.connect(**config)
            cursor = connection.cursor(dictionary=True)  # 设置为字典模式，使结果以字典形式返回
            cursor.execute(
                "UPDATE member SET name = %s WHERE username = %s", (new_name, session["username"]))
            connection.commit()
            member = cursor.fetchone()
            if cursor.rowcount > 0:
                session["name"] = new_name
                return jsonify(ok=True)
            else:
                return jsonify(error=True)

        except Exception as e:
            print(e)
            return jsonify(error=True)
        finally:
            cursor.close()
            connection.close()


if __name__ == "__main__":
    app.run(port=3000)
