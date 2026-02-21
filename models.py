from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# --- ASSOCIATION TABLES (Defined first to avoid reference errors) ---

experience_likes = db.Table('experience_likes',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('experience_id', db.Integer, db.ForeignKey('farmer_experiences.id', ondelete='CASCADE'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

comment_likes = db.Table('comment_likes',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('comment_id', db.Integer, db.ForeignKey('experience_comments.id', ondelete='CASCADE'), primary_key=True)
)

# --- MODELS ---

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False) 
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    is_active = db.Column(db.Boolean, default=True)
    
    # --- OTP FIELDS ---
    otp_code = db.Column(db.String(6))
    otp_expiry = db.Column(db.DateTime)
    otp_enabled = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    liked_experiences = db.relationship('FarmerExperience', secondary=experience_likes, back_populates='liked_by')

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
            'organization_id': self.organization_id,
            'is_active': self.is_active,
            'otp_enabled': self.otp_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Organization(db.Model):
    __tablename__ = 'organizations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text) 
    address = db.Column(db.Text) 
    
    contact_person = db.Column(db.String(255))
    contact_email = db.Column(db.String(255))
    contact_phone = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'description': self.description,
            'location': self.address,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone
        }

class Barangay(db.Model):
    __tablename__ = 'barangays'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
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

    id = db.Column(db.Integer, primary_key=True)
    farmer_code = db.Column(db.String(50), unique=True)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100), nullable=False)
    suffix = db.Column(db.String(20))
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    profile_image = db.Column(db.String(500))
    birth_date = db.Column(db.Date)
    
    barangay_id = db.Column(db.Integer, db.ForeignKey('barangays.id'), nullable=False)
    barangay = db.relationship('Barangay', backref='farmers')
    
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    organization = db.relationship('Organization', backref='farmers')
    
    data_encoder_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    data_encoder = db.relationship('User', backref='farmers_encoded')
    
    address = db.Column(db.Text)
    contact_number = db.Column(db.String(50))
    education_level = db.Column(db.String(50), nullable=False)
    annual_income = db.Column(db.Numeric(12, 2))
    income_source = db.Column(db.String(255))
    number_of_children = db.Column(db.Integer, default=0)
    children_farming_involvement = db.Column(db.Boolean, default=False)
    primary_occupation = db.Column(db.String(255))
    secondary_occupation = db.Column(db.String(255))
    farm_size_hectares = db.Column(db.Numeric(10, 2))
    land_ownership = db.Column(db.String(50))
    years_farming = db.Column(db.Integer)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    civil_status = db.Column(db.String(20), default='Single')

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name, self.suffix]
        return " ".join([p for p in parts if p]).strip()

    def get_image_url(self):
        if not self.profile_image: return None
        if self.profile_image.startswith(('http://', 'https://')): return self.profile_image
        if self.profile_image.startswith('/'): return self.profile_image
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
            'civil_status': self.civil_status,
            'profile_image': self.get_image_url(),
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
    farmer = db.relationship('Farmer', backref=db.backref('products', cascade='all, delete-orphan'))
    product_id = db.Column(db.Integer, db.ForeignKey('agricultural_products.id'), nullable=False)
    product = db.relationship('AgriculturalProduct')
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
    farmer = db.relationship('Farmer', backref=db.backref('children', cascade='all, delete-orphan'))
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

class ExperienceComment(db.Model):
    __tablename__ = 'experience_comments'
    id = db.Column(db.Integer, primary_key=True)
    experience_id = db.Column(db.Integer, db.ForeignKey('farmer_experiences.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User') 
    liked_by = db.relationship('User', secondary=comment_likes, backref=db.backref('liked_comments', lazy='dynamic'))

    def to_dict(self, current_user_id=None):
        try:
            uid = int(current_user_id) if current_user_id else None
        except:
            uid = None

        likes_list = self.liked_by if self.liked_by is not None else []

        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else 'Unknown',
            'text': self.text,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'likes_count': len(likes_list),
            'is_liked_by_me': any(int(u.id) == uid for u in likes_list) if uid else False
        }

class FarmerExperience(db.Model):
    __tablename__ = 'farmer_experiences'
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmers.id', ondelete='CASCADE'), nullable=False)
    farmer = db.relationship('Farmer', backref=db.backref('experiences', cascade='all, delete-orphan'))
    experience_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date_recorded = db.Column(db.Date)
    interviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    interviewer = db.relationship('User', foreign_keys=[interviewer_id])
    location = db.Column(db.String(255))
    context = db.Column(db.Text)
    impact_level = db.Column(db.String(20))
    comments_enabled = db.Column(db.Boolean, default=True) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    liked_by = db.relationship('User', secondary=experience_likes, back_populates='liked_experiences')
    comments = db.relationship('ExperienceComment', backref='experience', cascade='all, delete-orphan', order_by='ExperienceComment.created_at.asc()')

    def to_dict(self, include_relations=False, current_user_id=None):
        try:
            uid = int(current_user_id) if current_user_id else None
        except (ValueError, TypeError):
            uid = None

        likes_list = self.liked_by if self.liked_by is not None else []
        comments_list = self.comments if self.comments is not None else []

        data = {
            'id': self.id,
            'farmer_id': self.farmer_id,
            'experience_type': self.experience_type,
            'title': self.title,
            'description': self.description,
            'date_recorded': self.date_recorded.isoformat() if self.date_recorded else None,
            'location': self.location,
            'impact_level': self.impact_level,
            'comments_enabled': self.comments_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            
            'likes_count': len(likes_list),
            'is_liked_by_me': any(int(u.id) == uid for u in likes_list) if uid else False,
            
            'comments_count': len(comments_list),
            'comments': [c.to_dict(current_user_id=uid) for c in comments_list]
        }
        
        if include_relations:
            data['farmer_name'] = self.farmer.full_name if self.farmer else "Unknown"
        return data

class ResearchProject(db.Model):
    __tablename__ = 'research_projects'
    id = db.Column(db.Integer, primary_key=True)
    project_code = db.Column(db.String(50), unique=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    principal_investigator_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    principal_investigator = db.relationship('User')
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    organization = db.relationship('Organization')
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
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False, default='General') 
    target_group = db.Column(db.String(255))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'target_group': self.target_group,
            'created_by': self.created_by,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    user = db.relationship('User')
    action = db.Column(db.String(255), nullable=False)
    entity_type = db.Column(db.String(100))
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

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True) 
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
        
class TokenBlocklist(db.Model):
    __tablename__ = 'token_blocklist'
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "jti": self.jti,
            "created_at": self.created_at.isoformat()
        }