import os
import sys
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore import Client as FirestoreClient

# TODO: Replace 'your-project-id' with your actual Firebase project ID.
PROJECT_ID = 'qmulclub'
COLLECTION_NAME = 'notes'
DOCUMENT_NAME = 'simplenote_backup'
DATABASE_NAME = 'club' # Database name as requested

def get_firestore_db():
    """
    Initializes the Firestore client for a specific database using Application Default Credentials
    and verifies the connection.
    """
    try:
        # Initialize Firebase Admin SDK if not already done.
        # This uses Application Default Credentials by default.
        if not firebase_admin._apps:
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred, {
                'projectId': PROJECT_ID,
            })

        # Get the initialized app and its credentials
        app = firebase_admin.get_app()
        gcloud_cred = app.credential.get_credential()

        # Create a Firestore client for the specific database
        db = FirestoreClient(project=app.project_id, credentials=gcloud_cred, database=DATABASE_NAME)

        # Test the connection with a simple read operation.
        db.collection(COLLECTION_NAME).limit(1).get()
        print(f"Successfully connected to Firestore database: '{DATABASE_NAME}'")
        
        return db

    except Exception as e:
        print(f"Error connecting to Firestore database '{DATABASE_NAME}': {e}", file=sys.stderr)
        print("Please check your authentication (gcloud auth application-default login) "
              "and project configuration.", file=sys.stderr)
        return None

def backup_notes_to_firestore(db, notes):
    """
    Saves a list of notes to a single Firestore document.

    Args:
        db: An authenticated Firestore client instance.
        notes (list): A list of note dictionaries to save.
    """
    if not notes:
        print("No notes to backup.")
        return False
    
    if not db:
        print("Firestore database client is not available.", file=sys.stderr)
        return False

    try:
        doc_ref = db.collection(COLLECTION_NAME).document(DOCUMENT_NAME)
        doc_ref.set({
            'notes': notes,
            'last_updated': firestore.SERVER_TIMESTAMP
        })
        print(f"Successfully backed up {len(notes)} notes to Firestore.")
        return True
    except Exception as e:
        print(f"An error occurred while backing up to Firestore: {e}", file=sys.stderr)
        return False

def read_notes_from_firestore(db):
    """
    Reads the list of notes from a single Firestore document.

    Args:
        db: An authenticated Firestore client instance.

    Returns:
        list: A list of note dictionaries, or an empty list if not found or an error occurs.
    """
    if not db:
        print("Firestore database client is not available.", file=sys.stderr)
        return []

    try:
        doc_ref = db.collection(COLLECTION_NAME).document(DOCUMENT_NAME)
        doc = doc_ref.get()
        if doc.exists and 'notes' in doc.to_dict():
            return doc.to_dict()['notes']
        return [] # Return empty list if document or notes field doesn't exist
    except Exception as e:
        print(f"An error occurred while reading from Firestore: {e}", file=sys.stderr)
        return [] # Return empty list on error

def save_notes_to_firestore(db, notes, document_name):
    """
    Saves a list of notes to a single Firestore document with a dynamic document name.

    Args:
        db: An authenticated Firestore client instance.
        notes (list): A list of note dictionaries to save.
        document_name (str): The name of the document to save the notes to.
    """
    if not notes:
        print(f"No notes to save to document '{document_name}'.")
        return False

    if not db:
        print("Firestore database client is not available.", file=sys.stderr)
        return False
    notes_map = {note['key']:note for note in notes}
    try:
        doc_ref = db.collection(COLLECTION_NAME).document(document_name)
        doc_ref.set({
            'notes': notes_map,
            'last_updated': firestore.SERVER_TIMESTAMP
        },{ merge: true })
        print(f"Successfully saved {len(notes)} notes to Firestore document '{document_name}'.")
        return True
    except Exception as e:
        print(f"An error occurred while saving to Firestore document '{document_name}': {e}", file=sys.stderr)
        return False

def save_note_to_firestore(db, note, document_name):
    """
    Saves note to a single Firestore document with a dynamic document name.

    Args:
        db: An authenticated Firestore client instance.
        notes (list): A list of note dictionaries to save.
        document_name (str): The name of the document to save the notes to.
    """
    if not note:
        print(f"No note to save to document '{document_name}'.")
        return False

    if not db:
        print("Firestore database client is not available.", file=sys.stderr)
        return False

    try:
        doc_ref = db.collection(COLLECTION_NAME).document(document_name)
        doc_ref.set({
            'notes': {note['key']:note},
            'last_updated': firestore.SERVER_TIMESTAMP
        }, merge=True)
        print(f"Successfully saved note {note['key']} to Firestore document '{document_name}'.")
        return True
    except Exception as e:
        print(f"An error occurred while saving to Firestore document '{document_name}': {e}", file=sys.stderr)
        return False
