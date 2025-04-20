from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse as urlparse
from http import cookies

PORT = 8000

# Simulated database
employees = {}
next_id = 1

# Hardcoded login credentials
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"
SESSIONS = {}

def html_template(content):
    return f"""
    <html>
    <head>
        <title>Employee Manager</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: linear-gradient(to right, #f7c1d9, #f5a8c9);
                color: #333;
                margin: 0;
                padding: 20px;
            }}
            h1 {{
                text-align: center;
                color: white;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: #fff;
                margin-bottom: 30px;
            }}
            th, td {{
                padding: 12px;
                border: 1px solid #ccc;
                text-align: left;
            }}
            th {{
                background-color: #ff6b8c;
                color: white;
            }}
            tr:nth-child(even) {{
                background-color: #f9f1f4;
            }}
            form {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
                max-width: 500px;
                margin: 20px auto;
            }}
            input[type="text"],
            input[type="number"],
            input[type="password"] {{
                width: 100%;
                padding: 10px;
                margin: 8px 0;
                border: 1px solid #ccc;
                border-radius: 5px;
            }}
            input[type="submit"] {{
                background-color: #ff6b8c;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }}
            input[type="submit"]:hover {{
                background-color: #f5a8c9;
            }}
            a {{
                color: #ff6b8c;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            .error {{
                color: red;
                text-align: center;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <h1>Employee Management System</h1>
        {content}
    </body>
    </html>
    """

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        user = self.get_logged_in_user()

        if self.path == "/":
            if not user:
                self.show_login()
            else:
                self.show_dashboard()
        elif self.path.startswith("/edit"):
            if user:
                self.show_edit_form()
            else:
                self.redirect("/")
        elif self.path.startswith("/delete"):
            if user:
                self.handle_delete()
            else:
                self.redirect("/")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Page not found")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        data = dict(urlparse.parse_qsl(body))

        if self.path == "/login":
            if data.get("username") == ADMIN_USER and data.get("password") == ADMIN_PASS:
                self.send_response(302)
                self.send_header("Location", "/")
                cookie = cookies.SimpleCookie()
                cookie["session"] = "valid"
                cookie["session"]["path"] = "/"
                self.send_header("Set-Cookie", cookie.output(header='', sep=''))
                self.end_headers()
            else:
                self.show_login("Invalid credentials")
        elif self.path == "/add":
            self.handle_add(data)
        elif self.path.startswith("/edit"):
            self.handle_update(data)
        else:
            self.send_response(404)
            self.end_headers()

    def show_login(self, error=""):
        error_html = f"<p class='error'>{error}</p>" if error else ""
        html = f"""
        {error_html}
        <form method="POST" action="/login">
            <label>Username:</label>
            <input type="text" name="username" required><br>
            <label>Password:</label>
            <input type="password" name="password" required><br>
            <input type="submit" value="Login">
        </form>
        """
        self.send_html(html_template(html))

    def show_dashboard(self):
        employee_rows = "".join([ 
            f"<tr><td>{e['name']}</td><td>{e['position']}</td><td>{e['salary']}</td>"
            f"<td><a href='/edit?id={e['id']}'>Edit</a> | <a href='/delete?id={e['id']}'>Delete</a></td></tr>"
            for e in employees.values()
        ])
        table = f"""
        <table>
        <tr><th>Name</th><th>Position</th><th>Salary</th><th>Actions</th></tr>
        {employee_rows}
        </table>
        """

        form = """
        <h3>Add New Employee</h3>
        <form method="POST" action="/add">
            Name: <input type="text" name="name"><br>
            Position: <input type="text" name="position"><br>
            Salary: <input type="number" name="salary"><br>
            <input type="submit" value="Add Employee">
        </form>
        """

        self.send_html(html_template(table + form))

    def show_edit_form(self):
        query = urlparse.parse_qs(urlparse.urlparse(self.path).query)
        emp_id = int(query.get("id", [0])[0])
        emp = employees.get(emp_id)

        if not emp:
            self.send_html(html_template("<p>Employee not found.</p>"))
            return

        form = f"""
        <h3>Edit Employee</h3>
        <form method="POST" action="/edit?id={emp_id}">
            Name: <input type="text" name="name" value="{emp['name']}"><br>
            Position: <input type="text" name="position" value="{emp['position']}"><br>
            Salary: <input type="number" name="salary" value="{emp['salary']}"><br>
            <input type="submit" value="Update Employee">
        </form>
        """
        self.send_html(html_template(form))

    def handle_add(self, data):
        global next_id
        name = data.get("name")
        position = data.get("position")
        salary = data.get("salary")

        if not name or not position or not salary:
            self.send_html(html_template("<p>All fields are required.</p>"))
            return

        employees[next_id] = {
            "id": next_id,
            "name": name,
            "position": position,
            "salary": salary
        }
        next_id += 1
        self.redirect("/")

    def handle_update(self, data):
        query = urlparse.parse_qs(urlparse.urlparse(self.path).query)
        emp_id = int(query.get("id", [0])[0])
        emp = employees.get(emp_id)

        if emp:
            emp["name"] = data.get("name", emp["name"])
            emp["position"] = data.get("position", emp["position"])
            emp["salary"] = data.get("salary", emp["salary"])
        self.redirect("/")

    def handle_delete(self):
        query = urlparse.parse_qs(urlparse.urlparse(self.path).query)
        emp_id = int(query.get("id", [0])[0])
        employees.pop(emp_id, None)
        self.redirect("/")

    def send_html(self, html):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def redirect(self, location):
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    def get_logged_in_user(self):
        cookie = self.headers.get("Cookie")
        if not cookie:
            return None
        c = cookies.SimpleCookie(cookie)
        session = c.get("session")
        return session and session.value == "valid"

def run():
    print(f"Running on http://localhost:{PORT}")
    server = HTTPServer(("", PORT), Handler)
    server.serve_forever()

if __name__ == "__main__":
    run()
