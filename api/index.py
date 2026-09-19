from app import server

# Vercel expects a WSGI-compatible app object at the function entry point.
app = server
