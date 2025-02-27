from app import create_app

# Create app instance for WSGI servers
app = create_app()

if __name__ == '__main__':
    app.run()