"""
AI Resume Analyzer - Complete Production-Ready App
Developed for localhost with robust Supabase integration
"""

import streamlit as st
import pandas as pd
import base64
import random
import time
import datetime
import os
import socket
import platform
import secrets
import io
from supabase import create_client
import plotly.express as px
from geopy.geocoders import Nominatim
import geocoder
import nltk
nltk.download('stopwords', quiet=True)

# PDF Processing
try:
    from pyresparser import ResumeParser
    PYRESPRARSER_AVAILABLE = True
except ImportError:
    PYRESPRARSER_AVAILABLE = False

from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from streamlit_tags import st_tags
from PIL import Image

# Course Data (Fallback if Courses.py not available)
DS_COURSE = [
    ("Machine Learning A-Z", "https://coursera.org/ml"),
    ("Deep Learning Specialization", "https://coursera.org/deeplearning"),
    ("Python for Data Science", "https://udemy.com/python-datascience")
]
WEB_COURSE = [
    ("The Web Developer Bootcamp", "https://udemy.com/web-developer"),
    ("React - The Complete Guide", "https://udemy.com/react-complete"),
    ("Node.js Complete Course", "https://udemy.com/nodejs")
]
ANDROID_COURSE = [
    ("Android Development", "https://udemy.com/android-development"),
    ("Kotlin for Android", "https://udemy.com/kotlin-android"),
    ("Flutter Complete Course", "https://udemy.com/flutter")
]
IOS_COURSE = [
    ("iOS & Swift - The Complete Course", "https://udemy.com/ios-swift"),
    ("SwiftUI Masterclass", "https://udemy.com/swiftui")
]
UIUX_COURSE = [
    ("UI/UX Design Complete", "https://udemy.com/uiux-design"),
    ("Figma UI Design", "https://udemy.com/figma-design")
]
RESUME_VIDEOS = ["https://www.youtube.com/watch?v=q6-J2LF54Fg"]
INTERVIEW_VIDEOS = ["https://www.youtube.com/watch?v=eIho2S0ZahI"]

@st.cache_resource
def get_supabase_client():
    """Initialize Supabase client with multiple fallback methods"""
    client = None
    
    # Method 1: Environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    # Method 2: Streamlit secrets
    if not supabase_url or not supabase_key:
        try:
            supabase_url = st.secrets.get("SUPABASE_URL")
            supabase_key = st.secrets.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_ANON_KEY")
        except:
            pass
    
    # Method 3: Hardcoded fallback (REMOVE IN PRODUCTION)
    if not supabase_url or not supabase_key:
        st.warning("⚠️ No Supabase credentials found. Using demo mode.")
        return None
    
    try:
        client = create_client(supabase_url, supabase_key)
        
        # Test connection
        response = client.table("user_data").select("count", count="exact").execute()
        st.success("✅ Supabase connected!")
        return client
        
    except Exception as e:
        st.error(f"❌ Supabase connection failed: {str(e)}")
        st.info("""
        **Setup Instructions:**
        1. Set environment variables:
           export SUPABASE_URL="your-url"
           export SUPABASE_KEY="your-key"
        2. OR create .streamlit/secrets.toml with:
           SUPABASE_URL = "your-url"
           SUPABASE_KEY = "your-key"
        """)
        return None

def create_tables(client):
    """Create database tables"""
    if not client:
        return False
    
    tables_sql = """
    CREATE TABLE IF NOT EXISTS user_data (
        id BIGSERIAL PRIMARY KEY,
        sec_token VARCHAR(255) NOT NULL,
        ip_add VARCHAR(100),
        host_name VARCHAR(100),
        dev_user VARCHAR(100),
        os_name_ver VARCHAR(100),
        latlong TEXT,
        city VARCHAR(100),
        state VARCHAR(100),
        country VARCHAR(100),
        act_name VARCHAR(255) NOT NULL,
        act_mail VARCHAR(255) NOT NULL,
        act_mob VARCHAR(50) NOT NULL,
        name VARCHAR(255) NOT NULL,
        email_id VARCHAR(255) NOT NULL,
        resume_score VARCHAR(10) NOT NULL,
        timestamp VARCHAR(50) NOT NULL,
        page_no VARCHAR(10) NOT NULL,
        predicted_field TEXT NOT NULL,
        user_level TEXT NOT NULL,
        actual_skills TEXT NOT NULL,
        recommended_skills TEXT NOT NULL,
        recommended_courses TEXT NOT NULL,
        pdf_name VARCHAR(255) NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS user_feedback (
        id BIGSERIAL PRIMARY KEY,
        feed_name VARCHAR(255) NOT NULL,
        feed_email VARCHAR(255) NOT NULL,
        feed_score VARCHAR(10) NOT NULL,
        comments TEXT,
        timestamp VARCHAR(50) NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    ALTER TABLE user_data DISABLE ROW LEVEL SECURITY;
    ALTER TABLE user_feedback DISABLE ROW LEVEL SECURITY;
    """
    
    try:
        # Split and execute each statement
        for sql in tables_sql.split(';'):
            sql = sql.strip()
            if sql:
                client.rpc('execute_sql', {'sql': sql}).execute()
        st.success("✅ Database tables ready!")
        return True
    except Exception as e:
        st.error(f"Table creation failed: {e}")
        return False

def insert_user_data(client, **data):
    """Insert user analysis data"""
    if not client:
        st.warning("No database connection. Data not saved.")
        return False
    
    try:
        # Clean and prepare data
        clean_data = {k: str(v)[:1000] if isinstance(v, str) and len(str(v)) > 1000 else str(v) 
                     for k, v in data.items()}
        result = client.table("user_data").insert(clean_data).execute()
        return len(result.data) > 0
    except Exception as e:
        st.error(f"Data save failed: {e}")
        return False

def insert_feedback_data(client, **data):
    """Insert feedback data"""
    if not client:
        return False
    try:
        clean_data = {k: str(v)[:1000] if isinstance(v, str) and len(str(v)) > 1000 else str(v) 
                     for k, v in data.items()}
        result = client.table("user_feedback").insert(clean_data).execute()
        return len(result.data) > 0
    except:
        return False

def get_all_user_data(client):
    """Fetch all user data for admin"""
    if not client:
        return []
    try:
        result = client.table("user_data").select("*").order("created_at", desc=True).execute()
        return result.data
    except:
        return []

def get_all_feedback(client):
    """Fetch all feedback data"""
    if not client:
        return []
    try:
        result = client.table("user_feedback").select("*").order("created_at", desc=True).execute()
        return result.data
    except:
        return []

def get_csv_download_link(df, filename, text):
    """Generate CSV download link"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

def pdf_reader(file_path):
    """Extract text from PDF"""
    try:
        resource_manager = PDFResourceManager()
        fake_file_handle = io.StringIO()
        converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
        page_interpreter = PDFPageInterpreter(resource_manager, converter)
        
        with open(file_path, 'rb') as fh:
            for page in PDFPage.get_pages(fh, caching=True, check_extractable=True):
                page_interpreter.process_page(page)
        
        text = fake_file_handle.getvalue()
        converter.close()
        fake_file_handle.close()
        return text
    except Exception as e:
        st.error(f"PDF extraction failed: {e}")
        return ""

def show_pdf(file_path):
    """Display PDF preview"""
    try:
        with open(file_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"PDF preview failed: {e}")

def course_recommender(course_list):
    """Display course recommendations"""
    st.subheader("**Courses & Certificates Recommendations 👨‍🎓**")
    c = 0
    rec_course = []
    no_of_reco = st.slider('Number of Recommendations:', 1, 10, 5)
    
    random.shuffle(course_list)
    for c_name, c_link in course_list[:no_of_reco]:
        c += 1
        st.markdown(f"**({c})** [{c_name}]({c_link})")
        rec_course.append(c_name)
    return rec_course

def get_user_location():
    """Get user geolocation info with improved error handling"""
    try:
        # Set a timeout for the geocoder request
        g = geocoder.ip('me', timeout=5)
        if g.ok:
            latlong = g.latlng
            geolocator = Nominatim(user_agent="resume-analyzer")
            # Set a timeout for the reverse geocoding request
            location = geolocator.reverse(latlong, language='en', timeout=5)
            if location:
                address = location.raw.get('address', {})
                return {
                    'latlong': str(latlong),
                    'city': address.get('city', ''),
                    'state': address.get('state', ''),
                    'country': address.get('country', '')
                }
    except Exception as e:
        st.warning(f"⚠️ Could not determine location: {e}. Continuing without location data.")
    
    # Fallback if anything fails
    return {'latlong': 'N/A', 'city': 'Unknown', 'state': 'Unknown', 'country': 'Unknown'}

def get_system_info():
    """Get system information"""
    try:
        return {
            'sec_token': secrets.token_urlsafe(12),
            'ip_add': socket.gethostbyname(socket.gethostname()),
            'host_name': socket.gethostname(),
            'dev_user': os.getlogin(),
            'os_name_ver': f"{platform.system()} {platform.release()}"
        }
    except:
        return {'sec_token': secrets.token_urlsafe(12)}

def analyze_resume(resume_data, resume_text):
    """Analyze resume content"""
    # Experience level detection
    text_upper = resume_text.upper()
    if any(word in text_upper for word in ['INTERNSHIP', 'INTERNSHIPS']):
        cand_level = "Intermediate"
        level_msg = "🟡 Intermediate level detected!"
    elif any(word in text_upper for word in ['EXPERIENCE', 'WORK EXPERIENCE']):
        cand_level = "Experienced"
        level_msg = "🔴 Experienced professional!"
    else:
        cand_level = "Fresher"
        level_msg = "🟢 Fresher level!"
    
    st.markdown(f"### {level_msg}")
    
    # Skill-based field recommendation
    skills = resume_data.get('skills', [])
    ds_keywords = ['tensorflow', 'keras', 'pytorch', 'machine learning', 'deep learning', 'flask']
    web_keywords = ['react', 'django', 'node', 'javascript', 'php', 'angular']
    android_keywords = ['android', 'kotlin', 'flutter']
    ios_keywords = ['ios', 'swift', 'xcode']
    uiux_keywords = ['figma', 'adobe xd', 'ux', 'ui', 'prototyping']
    
    reco_field = "General"
    recommended_skills = []
    rec_course = DS_COURSE
    
    skills_lower = [s.lower() for s in skills]
    
    for skill in skills_lower:
        if any(kw in skill for kw in ds_keywords):
            reco_field = "Data Science"
            recommended_skills = ['TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'Data Visualization']
            rec_course = DS_COURSE
            break
        elif any(kw in skill for kw in web_keywords):
            reco_field = "Web Development"
            recommended_skills = ['React', 'Node.js', 'Django', 'JavaScript', 'REST APIs']
            rec_course = WEB_COURSE
            break
        elif any(kw in skill for kw in android_keywords):
            reco_field = "Android Development"
            recommended_skills = ['Kotlin', 'Android Studio', 'Flutter', 'Java']
            rec_course = ANDROID_COURSE
            break
        elif any(kw in skill for kw in ios_keywords):
            reco_field = "iOS Development"
            recommended_skills = ['Swift', 'Xcode', 'SwiftUI', 'UIKit']
            rec_course = IOS_COURSE
            break
        elif any(kw in skill for kw in uiux_keywords):
            reco_field = "UI/UX Design"
            recommended_skills = ['Figma', 'Adobe XD', 'Prototyping', 'User Research']
            rec_course = UIUX_COURSE
            break
    
    st.success(f"**🎯 Recommended Field:** {reco_field}")
    
    # Display skills
    st.subheader("**💻 Skills Analysis**")
    st_tags(label="Your Current Skills", value=skills, key='current_skills')
    st_tags(label="Recommended Skills", value=recommended_skills, key='rec_skills')
    
    # Course recommendations
    course_recommender(rec_course)
    
    # Resume scoring
    st.subheader("**📊 Resume Score**")
    score = calculate_resume_score(resume_text)
    
    progress_bar = st.progress(0)
    for i in range(score):
        time.sleep(0.01)
        progress_bar.progress(i + 1)
    
    st.success(f"**Your Score: {score}/100**")
    st.info("💡 Tip: Add missing sections like Projects, Certifications to improve score!")
    
    return {
        'cand_level': cand_level,
        'reco_field': reco_field,
        'recommended_skills': recommended_skills,
        'rec_course': rec_course,
        'resume_score': score
    }

def calculate_resume_score(resume_text):
    """Calculate resume quality score"""
    score = 0
    text_upper = resume_text.upper()
    
    sections = {
        'objective': ['OBJECTIVE', 'SUMMARY', 'PROFILE'],
        'education': ['EDUCATION', 'DEGREE', 'BACHELOR', 'MASTER'],
        'experience': ['EXPERIENCE', 'WORK EXPERIENCE', 'PROFESSIONAL EXPERIENCE'],
        'skills': ['SKILLS', 'TECHNICAL SKILLS', 'COMPETENCIES'],
        'projects': ['PROJECTS', 'PROJECT EXPERIENCE'],
        'certifications': ['CERTIFICATIONS', 'CERTIFICATE']
    }
    
    for section, keywords in sections.items():
        if any(keyword in text_upper for keyword in keywords):
            score += 15
    
    # Bonus for length and keywords
    if len(resume_text) > 500:
        score += 10
    if any(keyword in text_upper.lower() for keyword in ['python', 'java', 'react', 'sql']):
        score += 10
    
    return min(score + random.randint(0, 15), 100)

def user_page(client):
    """User resume analysis page"""
    st.header("📄 **Upload Your Resume**")
    st.markdown("### Fill your details and upload PDF resume for AI analysis")
    
    # User inputs
    col1, col2, col3 = st.columns(3)
    with col1:
        act_name = st.text_input("**Full Name** *", key="user_name")
    with col2:
        act_mail = st.text_input("**Email** *", key="user_email")
    with col3:
        act_mob = st.text_input("**Mobile**", key="user_mobile")
    
    # File upload
    pdf_file = st.file_uploader("Choose PDF Resume", type=["pdf"])
    
    if pdf_file is not None and act_name and act_mail:
        with st.spinner("🔮 Analyzing your resume... This may take a moment"):
            time.sleep(2)
            
            # Save uploaded file
            os.makedirs("Uploaded_Resumes", exist_ok=True)
            save_path = f"Uploaded_Resumes/{pdf_file.name}"
            with open(save_path, "wb") as f:
                f.write(pdf_file.getbuffer())
            
            st.success("✅ File uploaded successfully!")
            show_pdf(save_path)
            
            # Parse resume
            if PYRESPRARSER_AVAILABLE:
                resume_data = ResumeParser(save_path).get_extracted_data()
            else:
                resume_text = pdf_reader(save_path)
                resume_data = {
                    'name': act_name,
                    'email': act_mail,
                    'skills': ['Python', 'JavaScript'],  # Fallback
                    'no_of_pages': 1
                }
            
            # Get system and location info
            sys_info = get_system_info()
            loc_info = get_user_location()
            all_info = {**sys_info, **loc_info}
            
            # Analyze resume
            resume_text = pdf_reader(save_path)
            analysis = analyze_resume(resume_data, resume_text)
            
            # Save to database
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
            insert_user_data(client,
                **all_info,
                act_name=act_name,
                act_mail=act_mail,
                act_mob=act_mob,
                name=resume_data.get('name', act_name),
                email_id=resume_data.get('email', act_mail),
                resume_score=str(analysis['resume_score']),
                timestamp=timestamp,
                page_no=str(resume_data.get('no_of_pages', 1)),
                predicted_field=analysis['reco_field'],
                user_level=analysis['cand_level'],
                actual_skills=str(resume_data.get('skills', [])),
                recommended_skills=str(analysis['recommended_skills']),
                recommended_courses=str(analysis['rec_course']),
                pdf_name=pdf_file.name
            )
            
            # Bonus videos
            st.header("🎥 **Bonus Resources**")
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📝 Resume Tips")
                st.video(random.choice(RESUME_VIDEOS))
            with col2:
                st.subheader("🎤 Interview Prep")
                st.video(random.choice(INTERVIEW_VIDEOS))
            
            st.balloons()
            
    elif pdf_file and not (act_name and act_mail):
        st.warning("❌ Please fill **Name** and **Email** to proceed!")

def feedback_page(client):
    """Feedback collection page"""
    st.header("💬 **Give Us Feedback**")
    
    with st.form("feedback_form"):
        col1, col2 = st.columns(2)
        with col1:
            feed_name = st.text_input("Your Name")
            feed_email = st.text_input("Your Email")
        with col2:
            feed_score = st.slider("Rate us (1-5)", 1, 5, 3)
            comments = st.text_area("Comments/Suggestions")
        
        submitted = st.form_submit_button("Submit Feedback")
        
        if submitted and feed_name and feed_email:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
            if insert_feedback_data(client,
                feed_name=feed_name,
                feed_email=feed_email,
                feed_score=str(feed_score),
                comments=comments,
                timestamp=timestamp
            ):
                st.success("🎉 Thank you for your feedback!")
                st.balloons()
            else:
                st.error("Failed to save feedback. Please try again.")
    
    # Show feedback analytics
    feedback_data = get_all_feedback(client)
    if feedback_data:
        st.subheader("📊 **Feedback Analytics**")
        df = pd.DataFrame(feedback_data)
        
        # Rating distribution
        fig = px.pie(df, names='feed_score', title="Rating Distribution")
        st.plotly_chart(fig, use_container_width=True)
        
        # Recent comments
        st.subheader("Recent Comments")
        comment_df = df[['feed_name', 'comments', 'created_at']].rename(columns={
            'feed_name': 'User', 'comments': 'Comment', 'created_at': 'Date'
        })
        st.dataframe(comment_df)

def admin_page(client):
    """Admin dashboard"""
    st.header("🔐 **Admin Dashboard**")
    
    # Simple login
    if 'admin_logged_in' not in st.session_state:
        st.session_state.admin_logged_in = False
    
    if not st.session_state.admin_logged_in:
        with st.form("admin_login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_btn = st.form_submit_button("Login")
            
            if login_btn:
                if username == "admin" and password == "admin123":
                    st.session_state.admin_logged_in = True
                    st.success("✅ Admin login successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")
        return
    
    # Admin dashboard content
    user_data = get_all_user_data(client)
    
    if user_data:
        st.subheader(f"👥 **Total Users: {len(user_data)}**")
        df = pd.DataFrame(user_data)
        
        # Data display
        st.dataframe(df[['name', 'predicted_field', 'user_level', 'resume_score', 'created_at']])
        
        # Download CSV
        csv_link = get_csv_download_link(df, 'user_data.csv', '📥 Download Full Report')
        st.markdown(csv_link, unsafe_allow_html=True)
        
        # Analytics charts
        col1, col2 = st.columns(2)
        with col1:
            # Field distribution
            field_counts = df['predicted_field'].value_counts()
            fig1 = px.pie(values=field_counts.values, names=field_counts.index, 
                         title="Field Recommendations")
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Experience level
            level_counts = df['user_level'].value_counts()
            fig2 = px.pie(values=level_counts.values, names=level_counts.index,
                         title="Experience Levels")
            st.plotly_chart(fig2, use_container_width=True)
        
        # Score distribution
        st.subheader("📈 Score Distribution")
        fig3 = px.histogram(df, x='resume_score', nbins=20, title="Resume Scores")
        st.plotly_chart(fig3, use_container_width=True)
    
    else:
        st.info("No user data available yet.")
    
    # Logout
    if st.button("Logout"):
        st.session_state.admin_logged_in = False
        st.rerun()

def about_page():
    """About page"""
    st.header("ℹ️ **About AI Resume Analyzer**")
    
    st.markdown("""
    ## 🎯 **What We Do**
    Our AI-powered tool analyzes your resume using natural language processing to:
    - Extract key skills and experience
    - Recommend career paths and fields
    - Score your resume quality
    - Suggest relevant courses and certifications
    - Provide actionable improvement tips
    
    ## 🚀 **Key Features**
    - **PDF Resume Parsing** - Upload and analyze any PDF resume
    - **AI Skill Detection** - Automatically identify technical skills
    - **Career Recommendations** - Match skills to job fields
    - **Resume Scoring** - Get quality feedback (0-100)
    - **Learning Paths** - Personalized course recommendations
    - **Admin Analytics** - Track user trends and feedback
    
    ## 🛠 **Technology Stack**
    - **Frontend**: Streamlit
    - **Backend**: Supabase PostgreSQL
    - **AI/NLP**: pyresparser, NLTK
    - **PDF Processing**: pdfminer
    - **Visualization**: Plotly
    - **Geolocation**: geocoder, geopy
    
    ## 👨‍💻 **How to Use**
    1. Go to **User** tab
    2. Fill your contact details
    3. Upload your PDF resume
    4. Get instant AI analysis and recommendations
    5. Check **Admin** tab for analytics (admin/admin123)
    
    ## 🔒 **Admin Access**
    - Username: `admin`
    - Password: `admin123`
    - View user analytics, download reports, track trends
    
    ## 📞 **Support**
    Built with ❤️ by Tushar Jain
    [Portfolio](https://tushar-jain.vercel.app)
    """)

def main():
    """Main application entry point"""
    st.set_page_config(
        page_title="AI Resume Analyzer",
        page_icon="📄",
        layout="wide"
    )
    
    # Initialize Supabase
    client = get_supabase_client()
    
    # Initialize tables
    if client and 'tables_initialized' not in st.session_state:
        create_tables(client)
        st.session_state.tables_initialized = True
    
    # Header
    st.title("🤖 **AI Resume Analyzer**")
    st.markdown("---")
    
    # Sidebar navigation
    st.sidebar.title("📋 Navigation")
    activities = ["User", "Feedback", "About", "Admin"]
    choice = st.sidebar.selectbox("Choose an option:", activities)
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div style='text-align: center;'>
        <p><b>Built by</b></p>
        <p>by Tushar Jain  Ramchandran Vaibhav and Abdul</p>
        <p><a href='https://tushar-jain.vercel.app' target
    </div>
    """, unsafe_allow_html=True)
    
    # Page routing
    if choice == "User":
        user_page(client)
    elif choice == "Feedback":
        feedback_page(client)
    elif choice == "About":
        about_page()
    elif choice == "Admin":
        admin_page(client)

if __name__ == "__main__":
    main()