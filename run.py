import os
from app import create_app
from app.models import User
from app import db
from flask_migrate import Migrate

# Create app instance
app = create_app()

# Set up migration
migrate = Migrate(app, db)

@app.shell_context_processor
def make_shell_context():
    """Make objects available in the Flask shell."""
    return {'db': db, 'User': User}

@app.cli.command('create-admin')
def create_admin():
    """Create an admin user."""
    import getpass
    
    print("Creating admin user...")
    username = input("Username: ")
    
    # Check if username already exists
    if User.query.filter_by(username=username).first():
        print(f"User {username} already exists!")
        return
    
    email = input("Email: ")
    password = getpass.getpass("Password: ")
    confirm_password = getpass.getpass("Confirm password: ")
    
    if password != confirm_password:
        print("Passwords don't match!")
        return
    
    admin = User(username=username, email=email, subscription_level='admin')
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    print(f"Admin user {username} created successfully.")

@app.cli.command('init-db')
def init_db():
    """Initialize the database with default data."""
    print("Initializing database...")
    
    # Drop all tables
    db.drop_all()
    
    # Create all tables
    db.create_all()
    
    # Create admin user
    admin = User(
        username='admin',
        email='admin@example.com',
        subscription_level='admin'
    )
    admin.set_password('admin')
    
    # Create test user
    test_user = User(
        username='test',
        email='test@example.com',
        subscription_level='free'
    )
    test_user.set_password('test')
    
    # Add users to session
    db.session.add(admin)
    db.session.add(test_user)
    
    # Commit changes
    db.session.commit()
    
    print("Database initialized successfully.")

if __name__ == '__main__':
    # Run the application
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)