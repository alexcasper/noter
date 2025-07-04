import simplenote
import sys
import argparse
from datetime import datetime
from config import SIMPLENOTE_USER, SIMPLENOTE_PASS
from firestore import get_firestore_db, backup_notes_to_firestore


def get_simplenote_instance():
    """
    Authenticates with Simplenote and returns a Simplenote instance.

    Returns:
        A simplenote.Simplenote object on success, or None on failure.
    """
    try:
        # Authenticate with the Simplenote API
        sn = simplenote.Simplenote(SIMPLENOTE_USER, SIMPLENOTE_PASS)

        # The simplest way to verify authentication is to try a lightweight API call.
        _, status = sn.get_note_list(data=False)

        if status == 0:
            return sn
        else:
            print(f"Error authenticating with Simplenote. Status code: {status}", file=sys.stderr)
            return None

    except Exception as e:
        print(f"An error occurred during authentication: {e}", file=sys.stderr)
        return None

def get_note_title(content):
    """
    Extracts the title from a note's content, which is the first line.

    Args:
        content (str): The full content of the note.

    Returns:
        The first line of the content, or a placeholder if empty.
    """
    if not content:
        return "[No Title]"
    return content.split('', 1)[0].strip() or "[No Title]"

def list_notes(sn):
    """
    Fetches all notes, sorts them by modification date, and prints a list
    of titles and modification dates.

    Args:
        sn: An authenticated simplenote.Simplenote instance.
    """
    note_list, status = sn.get_note_list()
    if status != 0:
        print(f"Error fetching note list. Status: {status}", file=sys.stderr)
        return

    sorted_notes = sorted(note_list, key=lambda x: float(x.get('modifydate', 0)), reverse=True)

    print(f"Displaying {len(sorted_notes)} notes (newest first):")
    for note_meta in sorted_notes:
        # get_note_list doesn't include content, so we must fetch each note individually.
        note_full, status = sn.get_note(note_meta['key'])
        if status == 0:
            title = get_note_title(note_full.get('content'))
            modify_date = datetime.fromtimestamp(float(note_full.get('modifydate', 0)))
            print(f"{modify_date.strftime('%Y-%m-%d')} - {title}")
        else:
            print(f"  - Could not fetch content for note key {note_meta['key']}", file=sys.stderr)

def get_all_notes(sn):
    """
    Retrieves all notes with their full content from Simplenote.

    Args:
        sn: An authenticated simplenote.Simplenote instance.

    Returns:
        A list of note dictionaries, or an empty list on failure.
    """
    note_list, status = sn.get_note_list()
    if status != 0:
        print(f"Error fetching note list. Status: {status}", file=sys.stderr)
        return []

    all_notes = []
    for note_meta in note_list:
        note_full, status = sn.get_note(note_meta['key'])
        if status == 0:
            all_notes.append(note_full)
        else:
            print(f"  - Could not fetch content for note key {note_meta['key']}", file=sys.stderr)
    return all_notes

def main():
    """Main function to parse arguments and run commands."""
    parser = argparse.ArgumentParser(description="A simple CLI tool to interact with Simplenote.")
    parser.add_argument('command', nargs='?', default='list', choices=['list', 'backup'], help="The command to execute (default: list).")
    args = parser.parse_args()

    sn = get_simplenote_instance()
    if not sn:
        sys.exit(1)

    if args.command == 'list':
        list_notes(sn)
    elif args.command == 'backup':
        print("Backing up all notes to Firestore...")
        try:
                db = get_firestore_db()
                if db:
                    notes = get_all_notes(sn)
                    if notes:
                        backup_notes_to_firestore(db, notes)
                    else:
                        print("No notes to backup.", file=sys.stderr)
                else:
                    print("Firestore database client is not available.", file=sys.stderr)
        except:
            print("An error occurred while backing up to Firestore.", file=sys.stderr)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)

if __name__ == "__main__":
    main()