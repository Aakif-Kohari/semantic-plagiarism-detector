"""
User Management View Component.

Renders Tab 8 displaying system user management list.
"""

import streamlit as st
from src.db.auth import get_all_users


def render_users_view():
    """Render Tab 8: User Management."""
    st.subheader("👥 User Management")
    users = get_all_users()
    for u in users:
        st.write(f"User: **{u['username']}** | Role: `{u['role']}`")
