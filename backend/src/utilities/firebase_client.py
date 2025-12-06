import os
import firebase_admin
from firebase_admin import credentials, firestore

_CRED_PATH = os.path.join(
    os.path.dirname(__file__),
    "ezbuilt-dev-firebase-adminsdk-fbsvc-900cf233a6.json",
)

def init_firebase_if_needed():
    """Initialize the default Firebase app once."""
    if not firebase_admin._apps:
        cred = credentials.Certificate(_CRED_PATH)
        firebase_admin.initialize_app(cred)


def get_firestore_client():
    """Return a Firestore client, ensuring Firebase is initialized."""
    init_firebase_if_needed()
    return firestore.client()
