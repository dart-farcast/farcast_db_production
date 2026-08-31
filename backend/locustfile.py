"""
FarCast DB v2 — Modern Locust Load & Performance Testing Suite
Simulates concurrent multi-omics researchers and administrators querying the platform.
Run with:
  locust -f locustfile.py --host http://localhost:5052
Or headless:
  locust -f locustfile.py --headless -u 50 -r 10 --run-time 30s --host http://localhost:5052
"""
import random
from locust import HttpUser, task, between, events

TEST_DRUGS = ["Nivolumab", "Control", "Cisplatin", "Sunitinib", "Carboplatin"]
TEST_INDICATIONS = ["HNSCC", "Ca Breast", "RCC", "GI", "CRC"]
TEST_SEARCH_QUERIES = ["Niv", "Ca", "Bio", "Sun", "Cis"]

class ResearcherUser(HttpUser):
    """Simulates active scientific researchers querying multi-omics assay data."""
    wait_time = between(0.5, 2.0)
    weight = 4
    token = None

    def on_start(self):
        """Authenticate user on start."""
        res = self.client.post("/api/auth/login", json={
            "email": "admin@farcastbio.com",
            "password": "admin123"
        })
        if res.status_code == 200:
            self.token = res.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(5)
    def search_database(self):
        """Multi-select search query."""
        drug = random.choice(TEST_DRUGS)
        indication = random.choice(TEST_INDICATIONS)
        self.client.get(
            f"/api/search?drug={drug}&indication={indication}",
            headers=self.headers,
            name="/api/search [multi-filter]"
        )

    @task(4)
    def autocomplete_typing(self):
        """Prefix autocomplete query."""
        q = random.choice(TEST_SEARCH_QUERIES)
        self.client.get(
            f"/api/autocomplete?q={q}&field=drug",
            headers=self.headers,
            name="/api/autocomplete"
        )

    @task(3)
    def load_dashboard_stats(self):
        """Summary stats panel."""
        self.client.get(
            "/api/stats",
            headers=self.headers,
            name="/api/stats"
        )

    @task(1)
    def load_assay_types(self):
        """Assay metadata list."""
        self.client.get(
            "/api/assay_types",
            headers=self.headers,
            name="/api/assay_types"
        )


class AdminUser(HttpUser):
    """Simulates platform administrators accessing user management & audit feeds."""
    wait_time = between(1.0, 3.0)
    weight = 1
    token = None

    def on_start(self):
        res = self.client.post("/api/auth/login", json={
            "email": "admin@farcastbio.com",
            "password": "admin123"
        })
        if res.status_code == 200:
            self.token = res.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(2)
    def fetch_user_directory(self):
        self.client.get(
            "/api/admin/users",
            headers=self.headers,
            name="/api/admin/users"
        )

    @task(2)
    def fetch_whitelist_rules(self):
        self.client.get(
            "/api/admin/whitelist",
            headers=self.headers,
            name="/api/admin/whitelist"
        )

    @task(1)
    def fetch_audit_logs(self):
        self.client.get(
            "/api/admin/audit_logs",
            headers=self.headers,
            name="/api/admin/audit_logs"
        )
