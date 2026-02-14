from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False) 
    organization_id = db.Column(db.String(255)) 
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'organization': self.organization_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Organization(db.Model):
    __tablename__ = 'organizations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    contact_person = db.Column(db.String(255))
    contact_email = db.Column(db.String(255))
    contact_phone = db.Column(db.String(50))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'address': self.address
        }

class Barangay(db.Model):
    __tablename__ = 'barangays'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    municipality = db.Column(db.String(255), nullable=False)
    province = db.Column(db.String(255), nullable=False)
    region = db.Column(db.String(255), nullable=False)
    population = db.Column(db.Integer)
    total_households = db.Column(db.Integer)
    agricultural_households = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'municipality': self.municipality,
            'province': self.province,
            'region': self.region,
            'population': self.population,
            'total_households': self.total_households,
            'agricultural_households': self.agricultural_households
        }

class AgriculturalProduct(db.Model):
    __tablename__ = 'agricultural_products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'description': self.description
        }

class Farmer(db.Model):
    __tablename__ = 'farmers'

    # Column order matches your SQL schema exactly
    id = db.Column(db.Integer, primary_key=True)
    farmer_code = db.Column(db.String(50), unique=True)
    
    # Name Fields (positions 3-6)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100), nullable=False)
    suffix = db.Column(db.String(20))
    
    # Demographics (positions 7-8)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    
    # Profile Image (position 9) - BEFORE birth_date
    profile_image = db.Column(db.String(500))
    
    # Birth Date (position 10)
    birth_date = db.Column(db.Date)
    
    # Location & Relationships (positions 11-13)
    barangay_id = db.Column(db.Integer, db.ForeignKey('barangays.id'), nullable=False)
    barangay = relationship('Barangay', backref='farmers')
    
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    organization = relationship('Organization', backref='farmers')
    
    data_encoder_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    data_encoder = relationship('User', backref='farmers_encoded')
    
    # Contact Info (positions 14-15)
    address = db.Column(db.Text)
    contact_number = db.Column(db.String(50))
    
    # Socio-Economic (positions 16-22)
    education_level = db.Column(db.String(50), nullable=False)
    annual_income = db.Column(db.Numeric(12, 2))
    income_source = db.Column(db.String(255))
    number_of_children = db.Column(db.Integer, default=0)
    children_farming_involvement = db.Column(db.Boolean, default=False)
    primary_occupation = db.Column(db.String(255))
    secondary_occupation = db.Column(db.String(255))
    
    # Farm Details (positions 23-25)
    farm_size_hectares = db.Column(db.Numeric(10, 2))
    land_ownership = db.Column(db.String(50))
    years_farming = db.Column(db.Integer)
    
    # Timestamps (positions 26-27)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Helper for full name display
    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name, self.suffix]
        return " ".join([p for p in parts if p]).strip()

    def get_image_url(self):
        """
        Generate the proper image URL for the profile picture.
        Handles both absolute URLs (http/https) and relative paths.
        """
        if not self.profile_image:
            return None
        
        # If it's already an absolute URL (starts with http:// or https://), return as-is
        if self.profile_image.startswith(('http://', 'https://')):
            return self.profile_image
        
        # If it's a relative path starting with /, return as-is
        if self.profile_image.startswith('/'):
            return self.profile_image
        
        # Otherwise, construct full path assuming it's stored in uploads folder
        return f"/uploads/{self.profile_image}"

    def to_dict(self, include_relations=False):
        data = {
            'id': self.id,
            'farmer_code': self.farmer_code,
            'first_name': self.first_name,
            'middle_name': self.middle_name,
            'last_name': self.last_name,
            'suffix': self.suffix,
            'full_name': self.full_name,
            'age': self.age,
            'gender': self.gender,
            'profile_image': self.get_image_url(),  # Use helper method
            'birth_date': self.birth_date.isoformat() if self.birth_date else None,
            'barangay_id': self.barangay_id,
            'organization_id': self.organization_id,
            'address': self.address,
            'contact_number': self.contact_number,
            'education_level': self.education_level,
            'annual_income': float(self.annual_income) if self.annual_income else None,
            'income_source': self.income_source,
            'number_of_children': self.number_of_children,
            'children_farming_involvement': self.children_farming_involvement,
            'primary_occupation': self.primary_occupation,
            'secondary_occupation': self.secondary_occupation,
            'farm_size_hectares': float(self.farm_size_hectares) if self.farm_size_hectares else None,
            'land_ownership': self.land_ownership,
            'years_farming': self.years_farming,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_relations:
            data['barangay'] = self.barangay.to_dict() if self.barangay else None
            data['organization'] = self.organization.to_dict() if self.organization else None
            
        return data

class FarmerProduct(db.Model):
    __tablename__ = 'farmer_products'

    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmers.id', ondelete='CASCADE'), nullable=False)
    farmer = relationship('Farmer', backref=db.backref('products', cascade='all, delete-orphan'))
    
    product_id = db.Column(db.Integer, db.ForeignKey('agricultural_products.id'), nullable=False)
    product = relationship('AgriculturalProduct')
    
    production_volume = db.Column(db.Numeric(10, 2))
    unit = db.Column(db.String(50))
    is_primary = db.Column(db.Boolean, default=False)
    selling_price = db.Column(db.Numeric(10, 2))
    
    def to_dict(self):
        return {
            'id': self.id,
            'farmer_id': self.farmer_id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else None,
            'production_volume': float(self.production_volume) if self.production_volume else None,
            'unit': self.unit,
            'is_primary': self.is_primary,
            'selling_price': float(self.selling_price) if self.selling_price else None
        }

class FarmerChild(db.Model):
    __tablename__ = 'farmer_children'

    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmers.id', ondelete='CASCADE'), nullable=False)
    farmer = relationship('Farmer', backref=db.backref('children', cascade='all, delete-orphan'))
    
    name = db.Column(db.String(255))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    education_level = db.Column(db.String(100))
    continues_farming = db.Column(db.Boolean, default=False)
    involvement_level = db.Column(db.String(50), default='None')
    current_occupation = db.Column(db.String(255))
    notes = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'farmer_id': self.farmer_id,
            'name': self.name,
            'age': self.age,
            'gender': self.gender,
            'education_level': self.education_level,
            'continues_farming': self.continues_farming,
            'involvement_level': self.involvement_level,
            'current_occupation': self.current_occupation,
            'notes': self.notes
        }

class FarmerExperience(db.Model):
    __tablename__ = 'farmer_experiences'

    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmers.id', ondelete='CASCADE'), nullable=False)
    farmer = relationship('Farmer', backref=db.backref('experiences', cascade='all, delete-orphan'))
    
    experience_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date_recorded = db.Column(db.Date)
    
    interviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    interviewer = relationship('User')
    
    location = db.Column(db.String(255))
    context = db.Column(db.Text)
    impact_level = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self, include_relations=False):
        data = {
            'id': self.id,
            'farmer_id': self.farmer_id,
            'experience_type': self.experience_type,
            'title': self.title,
            'description': self.description,
            'date_recorded': self.date_recorded.isoformat() if self.date_recorded else None,
            'interviewer_id': self.interviewer_id,
            'location': self.location,
            'context': self.context,
            'impact_level': self.impact_level,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_relations:
            data['farmer_name'] = self.farmer.full_name if self.farmer else None
            data['interviewer_name'] = self.interviewer.full_name if self.interviewer else None
            
        return data

class ResearchProject(db.Model):
    __tablename__ = 'research_projects'

    id = db.Column(db.Integer, primary_key=True)
    project_code = db.Column(db.String(50), unique=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    principal_investigator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    principal_investigator = relationship('User')
    
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    organization = relationship('Organization')
    
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='Planning')
    research_type = db.Column(db.String(50), nullable=False)
    objectives = db.Column(db.Text)
    methodology = db.Column(db.Text)
    budget = db.Column(db.Numeric(15, 2))
    funding_source = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self, include_relations=False):
        data = {
            'id': self.id,
            'project_code': self.project_code,
            'title': self.title,
            'description': self.description,
            'principal_investigator_id': self.principal_investigator_id,
            'organization_id': self.organization_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status,
            'research_type': self.research_type,
            'objectives': self.objectives,
            'methodology': self.methodology,
            'budget': float(self.budget) if self.budget else None,
            'funding_source': self.funding_source,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_relations:
            data['principal_investigator_name'] = self.principal_investigator.full_name if self.principal_investigator else None
            data['organization_name'] = self.organization.name if self.organization else None
            
        return data

class SurveyQuestionnaire(db.Model):
    __tablename__ = 'survey_questionnaires'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('research_projects.id'))
    project = relationship('ResearchProject', backref='surveys')
    
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    survey_type = db.Column(db.String(50), nullable=False)
    target_group = db.Column(db.String(255))
    
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    creator = relationship('User')
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'title': self.title,
            'description': self.description,
            'survey_type': self.survey_type,
            'target_group': self.target_group,
            'created_by': self.created_by,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = relationship('User')
    
    action = db.Column(db.String(255), nullable=False)
    entity_type = db.Column(db.String(100))
    # Stores the ID of the affected entity as a string for flexibility
    entity_id = db.Column(db.String(100)) 
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else None,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
# Add this to your models.py
class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Ensure this matches your User model PK
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat(),
            "created_at_human": self.created_at.strftime("%b %d, %I:%M %p")
        }