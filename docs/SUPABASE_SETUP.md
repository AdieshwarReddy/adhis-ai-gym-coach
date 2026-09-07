# Supabase Cloud Setup Guide for Adhi's AI Gym Coach

This guide walks you through setting up a **100% Free-Tier** Supabase project to back **Adhi's AI Gym Coach** with PostgreSQL database storage, production user authentication, and Row Level Security (RLS).

---

## 1. Create a Free Supabase Account
1. Visit [supabase.com](https://supabase.com) and click **Start your project**.
2. Sign up with your GitHub or Google account (no credit card required on the free tier).

---

## 2. Create a New Project
1. In the Supabase dashboard, click **New project**.
2. Select your Organization.
3. Enter Project Name: `adhis-ai-gym-coach`.
4. Enter a strong **Database Password** (store this in your password manager).
5. Choose the closest region (e.g., `ap-south-1` for India / Mumbai, or closest to your users).
6. Select the **Free Tier** plan ($0/month).
7. Click **Create new project** and wait ~2 minutes for provisioning.

---

## 3. Retrieve Your API Credentials
1. In your project dashboard, navigate to the **Project Settings** (gear icon) on the left sidebar.
2. Under the **Configuration** menu, click **API**.
3. Under **Project URL**, copy the `URL` (e.g., `https://xyzcompany.supabase.co`).
4. Under **Project API keys**, copy the `anon` / `public` key (e.g., `eyJh...`).
   > ⚠️ **SECURITY WARNING:** Never copy or share the `service_role` secret in frontend or client applications. The `anon` key is strictly protected by Row Level Security (RLS).

---

## 4. Configure Authentication Settings
1. Navigate to **Authentication** -> **Providers** -> **Email**.
2. Ensure **Enable Email provider** is toggled **ON**.
3. Under **Confirm email**, you may optionally disable **Confirm email** during local development/testing so test accounts log in immediately without waiting for an email verification token.
4. Click **Save**.

---

## 5. Execute SQL Schema Migrations
1. Navigate to the **SQL Editor** tab (terminal icon) on the left sidebar.
2. Click **New query**.
3. Open the file `migrations/01_initial_schema.sql` in this repository and copy its entire contents.
4. Paste the SQL into the Supabase SQL Editor.
5. Click **Run** (green button).
6. You will see `Success. No rows returned`.
7. Verify tables created: Navigate to **Table Editor** to view:
   - `profiles`
   - `workout_sessions`
   - `exercise_sets`
   - `form_events`
   - `workout_summaries`

---

## 6. Verify Row Level Security (RLS)
1. In the **Table Editor**, notice each table shows a green shield icon labeled **RLS Enabled**.
2. Navigate to **Authentication** -> **Policies**.
3. Verify that policies for `profiles`, `workout_sessions`, `exercise_sets`, `form_events`, and `workout_summaries` are active:
   - User A can only read, insert, and update their own workouts and sets.
   - User B cannot see User A's data under any circumstances.

---

## 7. Configure Environment Credentials
### Option A: Local Development (`.env` or `.streamlit/secrets.toml`)
Create `.env` in the root folder:
```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOi...
GROQ_API_KEY=gsk_...
APP_ENV=development
```
Or create `.streamlit/secrets.toml`:
```toml
SUPABASE_URL = "https://your-project-id.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOi..."
GROQ_API_KEY = "gsk_..."
```

### Option B: Streamlit Community Cloud Deployment
1. Go to your app dashboard on [share.streamlit.io](https://share.streamlit.io).
2. Click **Settings** -> **Secrets**.
3. Paste the contents of your `secrets.toml`.
4. Click **Save**.

---

## 8. Test Your Connection
Run the verification test script:
```powershell
python -m pytest -v tests/test_supabase_connection.py
```
If Supabase credentials are not yet supplied, the system automatically and gracefully falls back to local SQLite (`Main App/data.db`) without crashing.
