import streamlit as st
from st_supabase_connection import SupabaseConnection

# Use flat secrets
def get_supabase_client():
    return st.connection(
        "supabase",
        type=SupabaseConnection,
        url=st.secrets["SUPABASE_URL"],
        key=st.secrets["SUPABASE_KEY"]
    )

st.header("🧪 Supabase Test")

st.subheader("Secrets Check")
has_url = "SUPABASE_URL" in st.secrets
has_key = "SUPABASE_KEY" in st.secrets
st.write(f"SUPABASE_URL present: {'✅' if has_url else '❌'}")
st.write(f"SUPABASE_KEY present: {'✅' if has_key else '❌'}")

client = get_supabase_client()
if client:
    st.success("✅ Supabase client created")
    try:
        client.table("user_data").select("count", count="exact").execute()
        client.table("user_feedback").select("count", count="exact").execute()
        st.success("✅ Tables accessible")
    except Exception as e:
        st.error(f"❌ Tables missing: {e}")
else:
    st.error("❌ Could not create Supabase client")
