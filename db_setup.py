import sqlite3

def setup_db():
    # Connect to the SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect("settings.db")
    c = conn.cursor()
    
    # Create the settings table if it doesn't exist
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            command_name TEXT PRIMARY KEY,
            state TEXT
        )
    """)
    
    # Create the custom commands table if it doesn't exist
    c.execute("""
        CREATE TABLE IF NOT EXISTS custom_commands (
            voice_command TEXT PRIMARY KEY,
            app_command TEXT
        )
    """)
    
    # Initialize default commands
    initialize_default_commands(c)
    
    conn.commit()
    conn.close()

def initialize_default_commands(cursor):
    # List of default commands
    default_commands = [
        "enter key", "delete key", "mouse click", "double click",
        "right click", "mouse drag", "mouse drop", "refresh page",
        "scroll up", "scroll down", "scroll up a bit", "scroll down a bit",
        "scroll up a little", "scroll down a little", "scroll to the top", 
        "scroll to the bottom", "keyboard undo", "mouse select all",
        "mouse copy", "mouse paste", "command window", "close window"
    ]
    
    # Insert each default command into the settings table with an initial state of 'off'
    for cmd in default_commands:
        cursor.execute("INSERT OR IGNORE INTO settings (command_name, state) VALUES (?, ?)", (cmd, "off"))

if __name__ == "__main__":
    setup_db()
