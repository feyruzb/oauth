from authlib.integrations.requests_client import OAuth2Session
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv
import random, os

# load from .env file
load_dotenv()

# Server config
hostName = os.getenv("HOST") if os.getenv("HOST") else "0.0.0.0"
serverPort = int(os.getenv("PORT")) if os.getenv("PORT") else 3000

# GitHub app config
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
scope = "user:email"

# Create an OAuth2Session instance
session = OAuth2Session(client_id, client_secret, scope=scope)

# Set the authorization endpoint and redirect URI
authorization_endpoint = "https://github.com/login/oauth/authorize"
redirect_uri = f"http://{hostName}:{serverPort}/callback"

# Users
users = {}

class MyServer(BaseHTTPRequestHandler):
    def page_template(self, title, content, headers=[]):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        for (header, value) in headers:
            self.send_header(header, value)
        self.end_headers()

        user = {
            "id": None,
            "login": "user",
            "name": "User",
            "image": "",
        }
        if self.is_logged_in():
            user = users[self.headers.get("Cookie").split("user=")[1].split(";")[0]]

        authorized_dropdown = f"""
        <div class="nav-item dropdown">
            <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                <img src='{user['image']}' class="rounded-circle" alt='avatar' width='20px'> {user['login']}
            </a>
            <div class="dropdown-menu">
                <a class="dropdown-item" href="https://github.com/{user['login']}">Profile</a>
                <li><hr class="dropdown-divider"></li>
                <a class="dropdown-item text-danger" href="/logout">Logout</a>
            </div>
        </div>"""


        self.wfile.write(bytes(f"""
        <html>
            <head>
                <title>{title}</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
            </head>
            <body>
                <nav class="navbar navbar-expand-md bg-body-tertiary">
                    <div class="container-md">
                        <a class="navbar-brand" href="/">Home</a>
                        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarSupportedContent" aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
                            <span class="navbar-toggler-icon"></span>
                        </button>
                        <div class="collapse navbar-collapse" id="navbarSupportedContent">
                            <div class="navbar-nav ms-auto">
                                {
                                    authorized_dropdown
                                    if self.is_logged_in() else
                                    "<a class='nav-link' href='/create_auth_url'>Login with GitHub</a>"
                                }
                            </div>
                        </div>
                    </div>
                </nav>
                <div class="container-md">
                    {content}
                </div>
                <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz" crossorigin="anonymous"></script>
            </body>
        </html>""", "utf-8"))
        return self.path

    def is_logged_in(self):
        if not self.headers.get("Cookie"):
            return False
        if not "user" in self.headers.get("Cookie"):
            return False
        user = self.headers.get("Cookie").split("user=")[1].split(";")[0]
        return user in [str(user_id) for user_id in users.keys()]

    def create_auth_url(self):
        uri, state = session.create_authorization_url(authorization_endpoint, redirect_uri=redirect_uri)
        return uri
    
    def get_user_info_by_token(self, token):
        client = OAuth2Session(client_id, token={"access_token": token, "token_type": "bearer"})
        return client.get("https://api.github.com/user").json()
    
    def home_page(self):
        if self.is_logged_in():
            user = users[self.headers.get("Cookie").split("user=")[1].split(";")[0]]
            info = self.get_user_info_by_token(user['token'])

            template = f"""
            <img src='{user['image']}' class="rounded-circle" alt='avatar' width='100px'>
            <h2>Welcome, {user['name']}.</h2>
            <p>
                You are logged in as: <a href="https://github.com/{user['login']}">@{user['login']}</a>
                <br>
                {info['bio'] if info['bio'] else ""}
            </p>

            <p>
                <i class="fa fa-list fa-fw"></i> Public repositories: {info['public_repos']} <a href="https://github.com/{user['login']}?tab=repositories">View</a><br>
                <i class="fa fa-code fa-fw"></i> Gists: {info['public_gists']} <a href="https://gist.github.com/{user['login']}">View</a><br>
                <i class="fa fa-users fa-fw"></i> Followers: {info['followers']}<br>
                <i class="fa fa-user fa-fw"></i> Following: {info['following']}<br>
                {"<i class='fa fa-map-marker fa-fw'></i> Location: " + info['location'] + "<br>" if info['location'] else ""}
                {"<i class='fa fa-building fa-fw'></i> Company: " + info['company'] + "<br>" if info['company'] else ""}
                {"<i class='fa fa-twitter fa-fw'></i> Twitter: " + info['twitter_username'] + "<br>" if info['twitter_username'] else ""}
            </p>
            """

            return self.page_template("Welcome", template, [])
        return self.page_template("Home", f"<h2>Welcome!</h2>", [])
    
    def process_callback(self):
        code, state = self.path.split('code=')[1].split('&')[0], self.path.split('state=')[1]
        token = session.fetch_token(
            url="https://github.com/login/oauth/access_token",
            authorization_response=f"http://{hostName}:{serverPort}/callback?code={code}&state={state}",
        )
        user = session.get("https://api.github.com/user").json()
        
        # user provided good credentials at GitHub
        if user:
            users[str(user['id'])] = {
                'login': user['login'],
                'name': user['name'],
                'token': token['access_token'],
                'image': user['avatar_url'] if user['avatar_url'] != '' else user['gravatar_id']
            }

            # send cookie to user
            return self.page_template("Welcome", f"<script>window.location.href = '/';</script>", [
                ("Set-Cookie", f"user={user['id']}; Path=*")
            ])

        return self.page_template("Error", "<h2>Invalid credentials</h2>", [])
    
    def logout(self):
        return self.page_template("Logged out", "<h2>Logged out!</h2><script>window.location.href = '/';</script>", [
            ("Set-Cookie", "user=; Path=*; Expires=Thu, 01 Jan 1970 00:00:00 GMT")
        ]) # self-destruction of cookie, as it was expired in the past

    def do_GET(self):
        if self.path == "/":
            return self.home_page()
        elif self.path == "/create_auth_url":
            return self.page_template("Redirecting...", "<code>Redirecting to GitHub...</code><script>window.location.href = '%s';</script>" % self.create_auth_url(), [])
        elif self.path.startswith("/callback"):
            return self.process_callback()
        elif self.path == "/logout":
            return self.logout()
        return self.path

webServer = HTTPServer(("0.0.0.0", serverPort), MyServer)
webServer.allow_reuse_address = True
print("Server started http://%s:%s" % (hostName, serverPort))

webServer.serve_forever()
webServer.server_close()
print("Server stopped.")
