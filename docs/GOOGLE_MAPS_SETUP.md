# Google Maps Integration & Setup Guide

**Application:** Adhi's AI Gym Coach  
**Module:** Cardio / Running & GPS Route Visualization  
**Free-First Default:** OpenStreetMap (OSM) via Leaflet is automatically active when no Google Maps API key is configured.

---

## 1. Overview & Architecture

Adhi's AI Gym Coach supports dual-engine mapping:
- **OpenStreetMap (OSM) + Leaflet (Default):** 100% Free, zero credit-card, zero billing, privacy-preserving, and works out of the box with dark-mode fitness tiles.
- **Google Maps JavaScript API:** High-resolution satellite & vector mapping with route polylines and custom start/finish pins.

---

## 2. Google Maps Platform Setup (Step-by-Step)

If you decide to enable Google Maps for production:

### Step 1: Create a Google Cloud Project
1. Navigate to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click the Project drop-down at the top and select **New Project**.
3. Name it `Adhi-AI-Gym-Coach` and click **Create**.

### Step 2: Enable Maps JavaScript API
1. In the console search bar, type **Maps JavaScript API**.
2. Click **Enable**.
3. *Note:* Do NOT enable Directions API, Places API, or Routes API unless specifically needed. Adhi's AI Gym Coach draws client-side GPS polylines directly on the map, requiring only the **Maps JavaScript API**.

### Step 3: Create a Dedicated API Key
1. Go to **APIs & Services > Credentials**.
2. Click **+ Create Credentials > API Key**.
3. Copy the newly generated key.

### Step 4: Apply Strict API Restrictions
1. Click **Edit API key** (pencil icon).
2. Under **API restrictions**, select **Restrict key**.
3. In the dropdown, check **ONLY** `Maps JavaScript API`.
4. Click **Save**.

### Step 5: Apply Website / HTTP Referrer Restrictions
To prevent unauthorized domains from consuming your quota:
1. Under **Application restrictions**, choose **Websites (HTTP referrers)**.
2. Add your authorized domains:
   - For local development: `http://localhost:*` and `http://127.0.0.1:*`
   - For Streamlit Cloud: `https://*.streamlit.app/*`
   - For custom domains: `https://yourdomain.com/*`
3. Click **Save**.

### Step 6: Billing & Pricing Caveats
> [!WARNING]
> Google Maps Platform requires linking a billing account to activate API keys. Google typically offers a monthly recurring credit ($200 USD free tier), but usage above that threshold is billed.
> If you prefer not to enter credit card details or want a strictly zero-cost deployment, keep `MAP_PROVIDER=osm` (OpenStreetMap).

### Step 7: Set Budget Alerts & Usage Quotas
1. Go to **Billing > Budgets & Alerts**.
2. Create a monthly alert at $1.00 USD and $10.00 USD.
3. Under **APIs & Services > Maps JavaScript API > Quotas**, set daily request limits (e.g. 1,000 requests/day) to prevent unexpected charges.

### Step 8: Configure Environment Variables
Add your key to `.env` (local) or Streamlit Secrets (cloud):

```bash
# In .env (Local)
GOOGLE_MAPS_API_KEY=AIzaSy...your_key_here...
MAP_PROVIDER=google
```

In `.streamlit/secrets.toml` (Streamlit Cloud):
```toml
GOOGLE_MAPS_API_KEY = "AIzaSy...your_key_here..."
MAP_PROVIDER = "google"
```

---

## 3. Switching Providers

You can switch between Google Maps and OpenStreetMap at any time via the environment variable or Streamlit secrets:

| Variable | Values | Description |
|---|---|---|
| `MAP_PROVIDER` | `osm` (default) or `google` | Active map engine |
| `GOOGLE_MAPS_API_KEY` | string | Your restricted Google Maps API key |

*If `GOOGLE_MAPS_API_KEY` is missing or empty, the application automatically falls back to OpenStreetMap without throwing errors.*
