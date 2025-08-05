from app import create_app

app = create_app()

# cors.init_app(app, resources={
#         r"/*": {
#             "origins": [
#                 "http://localhost:5173",  # Default React dev server
#                 "http://127.0.0.1:3000",  # Alternative local address
#                 # FRONTEND_URL  # Your future production frontend
#             ],
#             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
#             "allow_headers": ["Content-Type", "Authorization"],
#             "supports_credentials": True  # If using cookies/auth
#         }
#     })
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

    


