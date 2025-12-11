from app import app, db
from models import Admin, Department
from datetime import datetime

def init_database():
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if admin already exists
        admin = Admin.query.filter_by(username='admin').first()
        if not admin:
            # Create default admin
            admin = Admin(
                username='admin',
                email='admin@hospital.com'
            )
            admin.set_password('admin123')
            db.session.add(admin)
        
        # Create default departments if they don't exist
        departments = [
            {'name': 'Cardiology', 'description': 'Heart and cardiovascular system'},
            {'name': 'Orthopedics', 'description': 'Bones, joints, and muscles'},
            {'name': 'Neurology', 'description': 'Brain and nervous system'},
            {'name': 'Pediatrics', 'description': 'Children\'s health'},
            {'name': 'General Medicine', 'description': 'General health and wellness'},
        ]
        
        for dept_data in departments:
            dept = Department.query.filter_by(name=dept_data['name']).first()
            if not dept:
                dept = Department(**dept_data)
                db.session.add(dept)
        
        db.session.commit()
        print("Database initialized successfully!")
        print("Default Admin - Username: admin, Password: admin123")

if __name__ == '__main__':
    init_database()
