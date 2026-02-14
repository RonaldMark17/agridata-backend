import random
from datetime import datetime, timedelta, date
from faker import Faker
from app import create_app
from models import (
    db, User, Organization, Barangay, AgriculturalProduct, Farmer, 
    FarmerProduct, FarmerChild, FarmerExperience, ResearchProject,
    SurveyQuestionnaire, ActivityLog
)

# Initialize Faker
fake = Faker()
app = create_app()

def clear_data():
    """Deletes existing data to avoid duplicates (Order matters for Foreign Keys)"""
    print("🗑️  Cleaning old data...")
    meta = db.metadata
    for table in reversed(meta.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()
    print("✅ Database cleared.")

# --------------------------------------------------
# 1. REFERENCE TABLES (Orgs, Barangays, Products)
# --------------------------------------------------
def seed_references():
    print("🏗️  Seeding Reference Tables...")
    
    # --- Organizations ---
    org_types = ['LGU', 'Department_of_Agriculture', 'Research_Institution', 'Cooperative']
    orgs = []
    for _ in range(5):
        org = Organization(
            name=fake.company(),
            type=random.choice(org_types),
            contact_person=fake.name(),
            contact_email=fake.email(),
            contact_phone=fake.phone_number(),
            address=fake.address()
        )
        db.session.add(org)
        orgs.append(org)
    
    # --- Barangays (Sample Laguna Context) ---
    locations = [
        ("San Pablo City", "Laguna", ["San Francisco", "San Gabriel", "San Gregorio", "San Ignacio", "San Isidro"]),
        ("Calamba", "Laguna", ["Bucal", "Bunggo", "Burol", "Camaligan", "Canlubang"]),
        ("Santa Cruz", "Laguna", ["Bagumbayan", "Bubukal", "Calios", "Duhat", "Gatid"])
    ]
    
    barangays = []
    for muni, prov, brgy_list in locations:
        for b_name in brgy_list:
            brgy = Barangay(
                name=b_name,
                municipality=muni,
                province=prov,
                region="IV-A (Calabarzon)",
                population=random.randint(1000, 50000),
                total_households=random.randint(200, 10000),
                agricultural_households=random.randint(50, 5000)
            )
            db.session.add(brgy)
            barangays.append(brgy)

    # --- Agricultural Products ---
    product_list = [
        ("Rice (Palay)", "Crops"), ("Corn (Yellow)", "Crops"), ("Coconut", "Crops"),
        ("Mango", "Crops"), ("Banana (Lakatan)", "Crops"), ("Coffee (Robusta)", "Crops"),
        ("Carabao", "Livestock"), ("Cattle", "Livestock"), ("Goat", "Livestock"),
        ("Chicken (Broiler)", "Poultry"), ("Duck", "Poultry"),
        ("Tilapia", "Fishery"), ("Bangus", "Fishery")
    ]
    
    products = []
    for p_name, p_cat in product_list:
        prod = AgriculturalProduct(
            name=p_name,
            category=p_cat,
            description=fake.sentence()
        )
        db.session.add(prod)
        products.append(prod)

    db.session.commit()
    return orgs, barangays, products

# --------------------------------------------------
# 2. USERS
# --------------------------------------------------
def seed_users(orgs):
    print("busts  Seeding Users...")
    
    roles = ['admin', 'researcher', 'data_encoder']
    users = []
    
    # Create one explicit admin
    admin = User(
        username="admin",
        email="admin@agri.com",
        full_name="System Administrator",
        role="admin",
        organization_id=orgs[0].id
    )
    admin.set_password("password123")
    db.session.add(admin)
    users.append(admin)
    
    # Create random users
    for i in range(10):
        role = random.choice(roles)
        u = User(
            username=f"user{i}",
            email=fake.email(),
            full_name=fake.name(),
            role=role,
            organization_id=random.choice(orgs).id
        )
        u.set_password("password123")
        db.session.add(u)
        users.append(u)
        
    db.session.commit()
    return users

# --------------------------------------------------
# 3. FARMERS & DETAILS
# --------------------------------------------------
def seed_farmers(barangays, orgs, users, products):
    print("👨‍🌾 Seeding Farmers & Details...")
    
    encoders = [u for u in users if u.role in ['admin', 'data_encoder']]
    
    for i in range(50): # Create 50 farmers
        try:
            barangay = random.choice(barangays)
            birth_date = fake.date_of_birth(minimum_age=25, maximum_age=75)
            
            # 1. Create Farmer
            farmer = Farmer(
                farmer_code=f"AGRI-{date.today().year}-{str(i+1000)}",
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                age=date.today().year - birth_date.year,
                gender=random.choice(['Male', 'Female']),
                birth_date=birth_date,
                barangay_id=barangay.id,
                address=fake.address(),
                contact_number=fake.phone_number(),
                education_level=random.choice(['Elementary', 'High School', 'College']),
                annual_income=random.uniform(50000, 500000),
                income_source="Farming",
                years_farming=random.randint(1, 50),
                farm_size_hectares=random.uniform(0.5, 10.0),
                land_ownership=random.choice(['Owner', 'Tenant']),
                organization_id=random.choice(orgs).id,
                data_encoder_id=random.choice(encoders).id
            )
            db.session.add(farmer)
            db.session.commit() # Commit to get ID
            
            # 2. Add Farmer Products
            num_products = random.randint(1, 3)
            selected_prods = random.sample(products, num_products)
            
            for idx, prod in enumerate(selected_prods):
                fp = FarmerProduct(
                    farmer_id=farmer.id,
                    product_id=prod.id,
                    production_volume=random.uniform(100, 2000),
                    unit="kg",
                    is_primary=(idx == 0),
                    selling_price=random.uniform(20, 150)
                )
                db.session.add(fp)
            
            # 3. Add Farmer Children
            if random.choice([True, False]):
                child = FarmerChild(
                    farmer_id=farmer.id,
                    name=fake.first_name(),
                    age=random.randint(5, 30),
                    gender=random.choice(['Male', 'Female']),
                    education_level="High School",
                    continues_farming=random.choice([True, False])
                )
                db.session.add(child)

        except Exception as e:
            db.session.rollback()
            print(f"Error seeding farmer {i}: {e}")

    db.session.commit()

# --------------------------------------------------
# 4. RESEARCH PROJECTS
# --------------------------------------------------
def seed_projects(users, orgs):
    print("📊 Seeding Projects...")
    
    researchers = [u for u in users if u.role in ['admin', 'researcher']]
    
    for i in range(5):
        start = fake.date_this_year()
        proj = ResearchProject(
            project_code=f"RES-{random.randint(1000,9999)}",
            title=fake.catch_phrase(),
            description=fake.text(),
            principal_investigator_id=random.choice(researchers).id,
            organization_id=random.choice(orgs).id,
            start_date=start,
            end_date=start + timedelta(days=180),
            status=random.choice(['Active', 'Planning', 'Completed']),
            research_type="Quantitative",
            budget=random.uniform(100000, 1000000)
        )
        db.session.add(proj)
    
    db.session.commit()

# --------------------------------------------------
# RUNNER
# --------------------------------------------------
if __name__ == '__main__':
    with app.app_context():
        # Create tables first if they don't exist
        db.create_all()
        
        clear_data()
        
        # Seed in order of dependency
        orgs, barangays, products = seed_references()
        users = seed_users(orgs)
        seed_farmers(barangays, orgs, users, products)
        seed_projects(users, orgs)
        
        print("\n✅  Seeding Complete!")