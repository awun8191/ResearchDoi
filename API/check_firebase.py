import firebase_admin
from firebase_admin import credentials, firestore
import sys

try:
    cred = credentials.Certificate("service-account.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    collections = db.collections()
    print("Project is ACTIVE. Found collections:", [c.id for c in collections])
except Exception as e:
    print("ERROR:", e)
    sys.exit(1)
