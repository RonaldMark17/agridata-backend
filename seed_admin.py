from app import create_app
from models import User

app = create_app()

with app.app_context():
    # Check if admin already exists to avoid duplicates
    if not User.objects(username='admin').first():
        admin = User(
            username='admin',
            email='admin@agridata.com',
            full_name='System Administrator',
            role='admin',
            organization='Department of Agriculture'
        )
        
        # This handles the hashing automatically
        admin.set_password('admin123') 
        
        # Save to MongoDB
        admin.save()
        print("✅ Admin user created successfully!")
    else:
        print("⚠️  Admin user already exists.")