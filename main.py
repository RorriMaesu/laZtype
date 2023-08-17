import tkinter as tk
from tkinter import Canvas, StringVar, PhotoImage, Toplevel, Scrollbar, ttk
import speech_recognition as sr
import pyautogui
import time
import threading
from PIL import Image
import pytesseract
import os
import cv2
import numpy as np
import sqlite3

settings_img_png = None
settings_canvas = None
root_exists = True

optional_commands = [
    "enter key", "delete key", "mouse click", "double click",
    "right click", "mouse drag", "mouse drop", "refresh page",
    "scroll up", "scroll down", "scroll up a bit", "scroll down a bit",
    "scroll up a little", "scroll down a little", "scroll to the top", 
    "scroll to the bottom", "keyboard undo", "mouse select all",
    "mouse copy", "mouse paste", "command window", "close window"
]

root = tk.Tk()
root_exists = True
root.title("LaZtype")
root.geometry("600x278")
mouse_held_down = False

def on_root_destroy(event):
    global root_exists
    root_exists = False

root.bind('<Destroy>', on_root_destroy)


# Load Images
back_button_image = PhotoImage(file="static/back_button.png")
add_command_image = PhotoImage(file="static/add_a_custom_command.png")
submit_image = PhotoImage(file="static/submit.png")
bg_image = PhotoImage(file="static/laztype_bg.png")
bg_image_settings = PhotoImage(file="static/laztype_bg1.png")
settings_image = PhotoImage(file="static/settings.png")
option_on_button_image = PhotoImage(file="static/option_on.png")
option_off_button_image = PhotoImage(file="static/option_off.png")
on_button_image = PhotoImage(file="static/on.png")
off_button_image = PhotoImage(file="static/off.png")
mic_off_image = PhotoImage(file="static/mic_off.png")
mic_listening1_image = PhotoImage(file="static/mic_listening1.png")
mic_listening2_image = PhotoImage(file="static/mic_listening2.png")
logo_image = PhotoImage(file="static/laztype_logo.png")
# Load the settings_img.png
settings_img_png = PhotoImage(file="static/settings_img.png")
canvas = Canvas(root, width=600, height=278, bd=0, highlightthickness=0)
canvas.pack()
canvas.create_image(300, 139, image=bg_image)

# Variables
listening = False
status_var = StringVar(value="Off")
commands_only_mode = False

# Set the path to the Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

recognizer = sr.Recognizer()
stop_listening = threading.Event()



def is_command_enabled(cmd):
    return load_command_state(cmd) == "on"


def move_mouse_to_quadrant(command):
    screen_width, screen_height = pyautogui.size()
    quadrant_width, quadrant_height = screen_width / 2, screen_height / 2

    # Print the command for debugging
    print(f"Command received: {command}")

    # mouse to the center of the screen
    if 'mouse to the center' in command.lower():
        x, y = screen_width / 2, screen_height / 2

    # Determine the primary quadrant based on the letter and set the mouse position to its center
    elif 'a' in command.lower():
        x, y = quadrant_width / 2, quadrant_height / 2
    elif 'b' in command.lower():
        x, y = (3 * quadrant_width) / 2, quadrant_height / 2
    elif 'c' in command.lower() or 'see' in command.lower():
        x, y = quadrant_width / 2, (3 * quadrant_height) / 2
    elif 'd' in command.lower():
        x, y = (3 * quadrant_width) / 2, (3 * quadrant_height) / 2
    else:
        print("Invalid quadrant command.")
        return

    # If a number is provided, refine the location within the quadrant
    if '1' in command:
        x, y = x - quadrant_width / 4, y - quadrant_height / 4
    elif '2' in command:
        x, y = x + quadrant_width / 4, y - quadrant_height / 4
    elif '3' in command:
        x, y = x - quadrant_width / 4, y + quadrant_height / 4
    elif '4' in command:
        x, y = x + quadrant_width / 4, y + quadrant_height / 4

    print(f"Moving mouse to position: ({x}, {y})")
    pyautogui.moveTo(x, y)

def click_notification():
    notification_image = "static/notification.png"
    location = pyautogui.locateOnScreen(notification_image, confidence=0.8)
    if location:
        x, y, w, h = location
        pyautogui.click(x + w//2, y + h//2)
        print("Notification clicked!")
    else:
        print("Notification image not found on the screen.")



def click_submit():
    screenshot = pyautogui.screenshot()
    screenshot_np = np.array(screenshot)
    gray = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)
    for text in ["Submit", "Save"]:
        d = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        n_boxes = len(d['text'])
        for i in range(n_boxes):
            if d['conf'][i] > 60:
                if text.lower() in d['text'][i].lower():
                    (x, y, w, h) = (d['left'][i], d['top'][i], d['width'][i], d['height'][i])
                    pyautogui.click(x + w // 2, y + h // 2)
                    return True
    print("No 'Submit' or 'Save' buttons found!")
    return False

def get_custom_commands():
    conn = sqlite3.connect("settings.db")
    c = conn.cursor()
    c.execute("SELECT voice_command, app_command FROM custom_commands")
    commands = c.fetchall()
    conn.close()
    return {voice_cmd: app_cmd for voice_cmd, app_cmd in commands}



def recognize_speech():
    global commands_only_mode, mouse_held_down
    screen_width, screen_height = pyautogui.size()  # Get screen dimensions
    custom_commands = get_custom_commands()
    # Fetch custom commands
    while not stop_listening.is_set():
        custom_commands = get_custom_commands()  # Fetch custom commands at the beginning of each loop iteration
        with sr.Microphone() as source:
            text = ""  # Initialize text
            try:
                print("Listening...")
                audio = None
                # Use shorter timeouts and check the stop_listening event more frequently
                start_time = time.time()
                while (time.time() - start_time) < 10 and not stop_listening.is_set():
                    try:
                        audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)
                        break
                    except sr.WaitTimeoutError:
                        pass
                
                if stop_listening.is_set() or audio is None:
                    continue

                text = recognizer.recognize_google(audio)

                if text in custom_commands:  # Check this inside the try block
                    pyautogui.write(custom_commands[text] + ' ')
                    continue

                # Check for mode switch commands
                if "bad sloth" in text.lower():
                    commands_only_mode = True
                    canvas.itemconfig(mic_img, image=mic_off_image)
                elif "good sloth" in text.lower():
                    commands_only_mode = False
                    animate_mic()
                
                # Check for other voice commands
                if "mouse drag" in text.lower() and is_command_enabled("mouse drag"):
                    if not mouse_held_down:
                        pyautogui.mouseDown()
                        mouse_held_down = True

                elif "mouse drop" in text.lower() and is_command_enabled("mouse drop"):
                    if mouse_held_down:
                        pyautogui.mouseUp()
                        mouse_held_down = False

                elif "keyboard undo" in text.lower() and is_command_enabled("keyboard undo"):
                    pyautogui.hotkey('ctrl', 'z')

                elif "delete key" in text.lower() and is_command_enabled("delete key"):
                    pyautogui.press('backspace')

                elif "mouse select all" in text.lower() and is_command_enabled("mouse select all"):
                    pyautogui.hotkey('ctrl', 'a')

                elif "mouse copy" in text.lower() and is_command_enabled("mouse copy"):
                    pyautogui.hotkey('ctrl', 'c')

                elif "mouse paste" in text.lower() and is_command_enabled("mouse paste"):
                    pyautogui.hotkey('ctrl', 'v')

                elif "right click" in text.lower() and is_command_enabled("right click"):
                    pyautogui.rightClick()

                elif "mouse click" in text.lower() and is_command_enabled("mouse click"):
                    pyautogui.click()

                elif "command window" in text.lower() and is_command_enabled("command window"):
                    pyautogui.keyDown('win')
                    pyautogui.keyUp('win')

                elif "close window" in text.lower() and is_command_enabled("close window"):
                    pyautogui.hotkey('alt', 'f4')

                elif "mouse to the top" in text.lower() and is_command_enabled("mouse to the top"):
                    current_x, _ = pyautogui.position()
                    pyautogui.moveTo(current_x, 20)

                elif "mouse to the bottom" in text.lower() and is_command_enabled("mouse to the bottom"):
                    current_x, _ = pyautogui.position()
                    pyautogui.moveTo(current_x, screen_height - 20)

                elif "mouse up a lot" in text.lower() and is_command_enabled("mouse up a lot"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(current_x, current_y - 540)

                elif "mouse down a lot" in text.lower() and is_command_enabled("mouse down a lot"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(current_x, current_y + 540)

                elif "mouse up a tiny bit" in text.lower() and is_command_enabled("mouse up a tiny bit"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(current_x, current_y - 30)

                elif "mouse up a bit" in text.lower() and is_command_enabled("mouse up a bit"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(current_x, current_y - 65)

                elif "mouse up a little" in text.lower() and is_command_enabled("mouse up a little"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(current_x, current_y - 135)

                elif "mouse down a tiny bit" in text.lower() and is_command_enabled("mouse down a tiny bit"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(current_x, current_y + 30)

                elif "mouse down a bit" in text.lower() and is_command_enabled("mouse down a bit"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(current_x, current_y + 65)

                elif "mouse down a little" in text.lower() and is_command_enabled("mouse down a little"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(current_x, current_y + 135)

                elif "mouse up" in text.lower() and is_command_enabled("mouse up"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(current_x, current_y - 270)

                elif "mouse down" in text.lower() and is_command_enabled("mouse down"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(current_x, current_y + 270)

                elif "mouse far left" in text.lower() and is_command_enabled("mouse far left"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(current_x - 540, current_y)

                elif "mouse far right" in text.lower() and is_command_enabled("mouse far right"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(current_x + 540, current_y)

                elif "mouse nudge left" in text.lower() and is_command_enabled("mouse nudge left"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(current_x - 30, current_y)

                elif "mouse nudge right" in text.lower() and is_command_enabled("mouse nudge right"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(current_x + 30, current_y)

                elif "mouse left a bit" in text.lower() and is_command_enabled("mouse left a bit"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(current_x - 65, current_y)

                elif "mouse right a bit" in text.lower() and is_command_enabled("mouse right a bit"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(current_x + 65, current_y)

                elif "mouse left a little" in text.lower() and is_command_enabled("mouse left a little"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(current_x - 135, current_y)

                elif "mouse right a little" in text.lower() and is_command_enabled("mouse right a little"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(current_x + 135, current_y)

                elif "mouse left" in text.lower() and is_command_enabled("mouse left"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(current_x - 270, current_y)

                elif "mouse all the way left" in text.lower() and is_command_enabled("mouse all the way left"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(10, current_y)

                elif "mouse all the way right" in text.lower() and is_command_enabled("mouse all the way right"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(screen_width - 10, current_y)

                elif "mouse right" in text.lower() and is_command_enabled("mouse right"):
                    current_x, current_y = pyautogui.position()
                    pyautogui.moveTo(current_x + 270, current_y)

                elif "mouse to" in text.lower():
                    quadrant_command = text.split("mouse to")[-1].strip()
                    move_mouse_to_quadrant(quadrant_command)

                elif "click submit" in text.lower() and is_command_enabled("click submit"):
                    click_submit()

                elif "double click" in text.lower() and is_command_enabled("double click"):
                    pyautogui.doubleClick()

                elif "refresh page" in text.lower() and is_command_enabled("refresh page"):
                    pyautogui.hotkey('ctrl', 'f5')

                elif "check my notifications" in text.lower() and is_command_enabled("check my notifications"):
                    click_notification()

                elif "scroll down a bit" in text.lower() and is_command_enabled("scroll down a bit"):
                    pyautogui.scroll(-108)

                elif "scroll down a little" in text.lower() and is_command_enabled("scroll down a little"):
                    pyautogui.scroll(-405)

                elif "scroll down" in text.lower() and is_command_enabled("scroll down"):
                    pyautogui.scroll(-864)

                elif "scroll up a bit" in text.lower() and is_command_enabled("scroll up a bit"):
                    pyautogui.scroll(108)

                elif "scroll up a little" in text.lower() and is_command_enabled("scroll up a little"):
                    pyautogui.scroll(405)

                elif "scroll up" in text.lower() and is_command_enabled("scroll up"):
                    pyautogui.scroll(864)

                elif "scroll to the top" in text.lower() and is_command_enabled("scroll to the top"):
                    pyautogui.press('home')

                elif "scroll to the bottom" in text.lower() and is_command_enabled("scroll to the bottom"):
                    pyautogui.press('end')

                elif not commands_only_mode:
                    pyautogui.write(text + ' ')
                
            except sr.UnknownValueError:
                print("Unknown value error. Retrying...")
                continue
            except sr.RequestError:
                print("Request error. Retrying...")
                time.sleep(2)
                continue
            except Exception as e:
                print(f"An error occurred: {e}")
                break


def on_scroll(event, scrollbar, listbox):
    """Adjust the scrollbar to the listbox."""
    scrollbar.set(*listbox.yview())
    return 'break'

def on_mousewheel(event, scrollbar):
    """Handle mouse wheel scrolling."""
    scrollbar.yview_scroll(-1*(event.delta//120), "units")
    return 'break'

class Tooltip:
    def __init__(self, canvas, item_id, button_id, text):
        self.canvas = canvas
        self.item_id = item_id
        self.button_id = button_id
        self.text = text
        self.tooltip_window = None

    def bind_to_canvas_item(self):
        self.canvas.tag_bind(self.item_id, "<Enter>", self.show_tooltip)
        self.canvas.tag_bind(self.item_id, "<Leave>", self.hide_tooltip)
        if self.button_id:
            self.canvas.tag_bind(self.button_id, "<Enter>", self.show_tooltip)
            self.canvas.tag_bind(self.button_id, "<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        x, y, _, _ = self.canvas.bbox(self.item_id)
        x += self.canvas.winfo_rootx() + 20
        y += self.canvas.winfo_rooty() + 20
        self.tooltip_window = Toplevel(self.canvas)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip_window, text=self.text, background="#ffffe0", relief=tk.SOLID, borderwidth=1)
        label.pack()

    def hide_tooltip(self, event):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

def open_settings(event):
    global settings_canvas

    if not root_exists:
        return

    if root.winfo_exists() and root.state() == 'withdrawn':
        root.deiconify()


    # Check if there's an existing settings window; if so, bring it to the front
    try:
        settings_canvas.winfo_exists()
        settings_canvas.tag_raise(tk.ALL)  # Raise all tags to bring the settings window to the front
        return
    except (AttributeError, tk.TclError):
        pass  # This means the settings_canvas doesn't exist or its window was destroyed

    # Create the settings window as a Toplevel widget
    settings_window = Toplevel(root)
    settings_window.title("Settings")
    settings_window.geometry("1200x800")

    # Create the canvas for the settings window
    settings_canvas = Canvas(settings_window, width=1200, height=800, bd=0, highlightthickness=0)
    settings_canvas.pack(fill="both", expand=True)

    # Set the background image
    settings_canvas.create_image(600, 400, image=bg_image_settings)

    #Back button for the settings screen
    back_button_id = settings_canvas.create_image(30, 30, image=back_button_image, anchor=tk.NW)
    settings_canvas.tag_bind(back_button_id, '<Button-1>', lambda e: settings_window.destroy())



    # Add the settings image to the top center of the settings menu
    settings_canvas.create_image(324, settings_img_png.height() // .716, image=settings_img_png)

    # Font for the command text
    font_tuple = ("Arial", 9)  # Adjust the font and size as needed

    # Create canvas items for each command in a 5x6 grid
    for i, cmd in enumerate(optional_commands):
        row, col = divmod(i, 5)  # Calculate the row and column for the current command using 5x6 grid
        state = load_command_state(cmd)
        img = option_on_button_image if state == "on" else option_off_button_image
        x_offset = 30 + (col * 108)  # Adjusted for 5 items horizontally
        y_offset_button = 234 + (row * 108)
        button_id = settings_canvas.create_image(x_offset + 50, y_offset_button, image=img, anchor=tk.W)
        settings_canvas.tag_bind(button_id, '<Button-1>', lambda e, cmd=cmd, item_id=button_id: toggle_canvas_command_state(cmd, item_id))
        y_offset_text = y_offset_button + 50
        cmd_text = settings_canvas.create_text(x_offset + 72, y_offset_text, text=cmd.title(), font=font_tuple, anchor=tk.CENTER)
        tooltip_msg = f"This option is for the '{cmd}' command."
        tooltip = Tooltip(settings_canvas, cmd_text, button_id, tooltip_msg)
        tooltip.bind_to_canvas_item()

    # Call the display_custom_commands function
    display_custom_commands()

    y_offset_custom_btn = 108  # Adjusted for 5x6 layout
    add_command_btn = settings_canvas.create_image(913, y_offset_custom_btn, image=add_command_image, anchor=tk.CENTER) 

    settings_canvas.tag_bind(add_command_btn, '<Button-1>', add_custom_command)

    # Call the display_custom_commands function
    display_custom_commands()


def display_custom_commands():
    """Function to display custom commands in the settings window."""
    # Starting positions for the custom commands
    x_offset_custom_command = 678
    y_offset_custom_command = 234
    
    # Spacing values
    x_spacing = 108
    y_spacing = 108

    # Font for the command text
    font_tuple = ("Arial", 9)  # Adjust the font and size as needed
    
    custom_commands_dict = get_custom_commands()
    
    # We'll enumerate the custom commands to get both the index and the command
    for i, (voice_command, app_command) in enumerate(custom_commands_dict.items()):
        row, col = divmod(i, 5)  # Adjusted for 5x6 layout
        
        # Calculate x and y offsets based on the index
        x = x_offset_custom_command + (col * x_spacing)
        y = y_offset_custom_command + (row * y_spacing)

        # Check the command state (assuming it's saved similarly to default ones)
        state = load_command_state(voice_command)
        img = option_on_button_image if state == "on" else option_off_button_image
        
        # Create the toggle button for the custom command
        button_id = settings_canvas.create_image(x, y, image=img, anchor=tk.W)
        settings_canvas.tag_bind(button_id, '<Button-1>', lambda e, cmd=voice_command, item_id=button_id: toggle_canvas_command_state(cmd, item_id))
        
        # Create the text under the toggle button
        cmd_text = settings_canvas.create_text(x + 22, y + 50, text=voice_command.title(), font=font_tuple, anchor=tk.CENTER)
        
        # Tooltip for the custom command (assuming it's the same as for the default commands)
        tooltip_msg = f"This option is for the '{voice_command}' command."
        tooltip = Tooltip(settings_canvas, cmd_text, button_id, tooltip_msg)
        tooltip.bind_to_canvas_item()







def save_command_state(cmd, state):
    conn = sqlite3.connect("settings.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (command_name, state) VALUES (?, ?)", (cmd, state))
    conn.commit()
    conn.close()
    print(f"Saved state of {cmd} as {state}")

def load_command_state(cmd):
    conn = sqlite3.connect("settings.db")
    c = conn.cursor()
    c.execute("SELECT state FROM settings WHERE command_name=?", (cmd,))
    state = c.fetchone()
    conn.close()
    print(f"Loaded state of {cmd} as {state[0] if state else 'off'}")
    return state[0] if state else "off"



def toggle_canvas_command_state(command_name, button_id):
    global settings_canvas  # Declare settings_canvas as global

    # Check the current state from the database
    current_state = load_command_state(command_name)
    
    # Toggle the state
    new_state = "on" if current_state == "off" else "off"
    
    # Save the new state to the database
    save_command_state(command_name, new_state)
    
    # Update the button image based on the new state
    new_image = option_on_button_image if new_state == "on" else option_off_button_image

    
    settings_canvas.itemconfig(button_id, image=new_image)

def stop_all_threads():
    """Stop all background threads."""
    stop_listening.set()  # Stops the recognize_speech thread

def exit_app():
    """Exit the application."""
    stop_all_threads()
    root.quit()
    root.destroy()
    os._exit(0)  # Close the app

def hide_main_window():
    """Hide the main window and exit the app."""
    exit_app()

def toggle_listening(event):
    global listening
    if listening:
        listening = False
        canvas.itemconfig(power_btn, image=off_button_image)  # Set to off image
        canvas.itemconfig(mic_img, image=mic_off_image)
        stop_listening.set()  # Stop the recognize_speech thread
    else:
        listening = True
        canvas.itemconfig(power_btn, image=on_button_image)  # Set to on image
        stop_listening.clear()
        threading.Thread(target=recognize_speech).start()
        animate_mic()


def add_custom_command(event):
    custom_command_window = Toplevel(root)
    custom_command_window.title("Add Custom Command")
    
    voice_command_label = tk.Label(custom_command_window, text="Voice Command:")
    voice_command_label.pack(padx=10, pady=5)
    
    voice_command_entry = tk.Entry(custom_command_window)
    voice_command_entry.pack(padx=10, pady=5)
    
    app_command_label = tk.Label(custom_command_window, text="App Command:")
    app_command_label.pack(padx=10, pady=5)
    
    # Use a Combobox for app command selection
    app_command_combobox = ttk.Combobox(custom_command_window, values=optional_commands)
    app_command_combobox.pack(padx=10, pady=5)

    # Adjust the button command to get the selected value from the combobox
    add_button = tk.Button(custom_command_window, image=submit_image, command=lambda: submit_custom_command(voice_command_entry.get(), app_command_combobox.get(), custom_command_window))
    add_button.pack(pady=10)
    return custom_command_window

def hide_main_window():
    root.withdraw()
    
# Bind this function to the main window's close button
root.protocol("WM_DELETE_WINDOW", hide_main_window)


def submit_custom_command(voice_command, app_command, custom_command_window):
    conn = sqlite3.connect("settings.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO custom_commands (voice_command, app_command) VALUES (?, ?)", (voice_command, app_command))
        conn.commit()
        print(f"Added custom command: {voice_command} -> {app_command}")
    except sqlite3.IntegrityError:
        print(f"Voice command '{voice_command}' already exists!")
    finally:
        conn.close()

    # Close the add custom command window directly without getting the top-level window
    custom_command_window.destroy()

    # Destroy the current settings window (if it exists) to ensure the refreshed one is shown
    global settings_canvas
    if settings_canvas:
        settings_canvas.master.destroy()
        settings_canvas = None

    # Reopen the settings window
    open_settings(None)




def animate_mic():
    if listening and not commands_only_mode:
        canvas.itemconfig(mic_img, image=mic_listening1_image)
        root.after(500, lambda: canvas.itemconfig(mic_img, image=mic_listening2_image) if listening else None)
        root.after(1000, animate_mic)
    elif not listening or commands_only_mode:
        canvas.itemconfig(mic_img, image=mic_off_image)
    
    # Save the new state to persistent storage (this part is just a placeholder)
    # save_to_storage(command_name, not current_state)

# UI Elements
canvas.create_image(300, 108, image=logo_image)
settings_btn = canvas.create_image(530, 35, image=settings_image)
canvas.tag_bind(settings_btn, '<Button-1>', open_settings)
power_btn = canvas.create_image(300, 234, image=off_button_image)
canvas.tag_bind(power_btn, '<Button-1>', toggle_listening)
mic_img = canvas.create_image(46, 52, image=mic_off_image)



# For the power button
power_btn_tooltip = Tooltip(canvas, power_btn, None, "Toggle voice recognition")
power_btn_tooltip.bind_to_canvas_item()

# For the settings button
settings_btn_tooltip = Tooltip(canvas, settings_btn, None, "Open settings")
settings_btn_tooltip.bind_to_canvas_item()

root.bind('<Escape>', lambda event: exit_app())


root.mainloop()