import streamlit as st
from services.auth.supabase_auth import sign_up, sign_in, reset_password


def _init_auth_state():
    for key in ["auth_mode", "auth_error", "auth_info"]:
        if key not in st.session_state:
            st.session_state[key] = "login" if key == "auth_mode" else ""


def render_login_wall() -> bool:
    """
    Renders a professional Sign In / Sign Up wall.
    Returns True once the user is authenticated.
    """
    if st.session_state.get("user_id") is not None:
        return True

    _init_auth_state()

    # ── Page header ────────────────────────────────────────────
    st.markdown(
        """
        <div style="text-align:center; padding: 2rem 0 1rem 0;">
            <div style="font-size:3rem;">🏋️‍♂️</div>
            <h1 style="font-size:2rem; font-weight:700; margin:0.25rem 0; letter-spacing:0.03em;">
                ADHI'S AI GYM COACH
            </h1>
            <p style="color:#9ca3af; font-size:0.95rem; margin:0;">
                Real-Time Pose Analysis · Rep Tracking · Intelligent Coaching
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Mode toggle ────────────────────────────────────────────
    col_login, col_signup = st.columns(2)
    with col_login:
        if st.button(
            "Sign In",
            key="tab_login",
            width='stretch',
            type="primary" if st.session_state.auth_mode == "login" else "secondary",
        ):
            st.session_state.auth_mode = "login"
            st.session_state.auth_error = ""
            st.session_state.auth_info = ""
            st.rerun()
    with col_signup:
        if st.button(
            "Create Account",
            key="tab_signup",
            width='stretch',
            type="primary" if st.session_state.auth_mode == "signup" else "secondary",
        ):
            st.session_state.auth_mode = "signup"
            st.session_state.auth_error = ""
            st.session_state.auth_info = ""
            st.rerun()

    st.markdown("<div style='margin-top:0.5rem;'></div>", unsafe_allow_html=True)

    # Show feedback banners
    if st.session_state.get("auth_error"):
        st.error(st.session_state.auth_error)
    if st.session_state.get("auth_info"):
        st.info(st.session_state.auth_info)

    # ── SIGN IN FORM ────────────────────────────────────────────
    if st.session_state.auth_mode == "login":
        with st.form("signin_form", clear_on_submit=False):
            st.markdown("#### Sign In")
            email = st.text_input("Email address", placeholder="you@example.com", key="login_email")
            password = st.text_input("Password", type="password", placeholder="••••••••", key="login_password")
            col_btn, col_reset = st.columns([2, 1])
            with col_btn:
                submitted = st.form_submit_button("Sign In →", width='stretch')
            with col_reset:
                reset_clicked = st.form_submit_button("Forgot?", width='stretch')

        if submitted:
            st.session_state.auth_error = ""
            result = sign_in(email, password)
            if result["success"]:
                user = result["user"]
                st.session_state.user_id = user["id"]
                st.session_state.username = user["display_name"]
                st.session_state.user_email = user["email"]
                st.session_state.is_cloud_user = user.get("is_cloud", False)
                st.rerun()
            else:
                st.session_state.auth_error = result["error"]
                st.rerun()

        if reset_clicked:
            if email:
                res = reset_password(email)
                st.session_state.auth_info = res.get("message", "Password reset sent.")
            else:
                st.session_state.auth_error = "Enter your email above to reset your password."
            st.rerun()

    # ── SIGN UP FORM ────────────────────────────────────────────
    elif st.session_state.auth_mode == "signup":
        with st.form("signup_form", clear_on_submit=False):
            st.markdown("#### Create Account")
            display_name = st.text_input("Your name", placeholder="e.g. Adhi", key="signup_name")
            email = st.text_input("Email address", placeholder="you@example.com", key="signup_email")
            password = st.text_input("Password (min 6 characters)", type="password", placeholder="••••••••", key="signup_password")
            confirm = st.text_input("Confirm password", type="password", placeholder="••••••••", key="signup_confirm")
            submitted = st.form_submit_button("Create Account →", width='stretch')

        if submitted:
            st.session_state.auth_error = ""
            if password != confirm:
                st.session_state.auth_error = "Passwords do not match."
                st.rerun()
            else:
                result = sign_up(email, password, display_name)
                if result["success"]:
                    user = result["user"]
                    st.session_state.user_id = user["id"]
                    st.session_state.username = user["display_name"]
                    st.session_state.user_email = user["email"]
                    st.session_state.is_cloud_user = user.get("is_cloud", False)
                    st.session_state.is_new_user = True  # First-time signup flag
                    st.session_state.auth_info = f"Welcome, {user['display_name']}! Account created successfully."
                    st.rerun()
                else:
                    st.session_state.auth_error = result["error"]
                    st.rerun()

    # ── Privacy notice ─────────────────────────────────────────
    st.markdown(
        """
        <div style="text-align:center; margin-top:2rem; color:#6b7280; font-size:0.8rem;">
            🔒 Camera frames are processed locally for pose analysis and are not stored.<br>
            Your workout data is saved securely and visible only to you.
        </div>
        """,
        unsafe_allow_html=True,
    )

    return False