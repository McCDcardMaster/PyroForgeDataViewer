import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, font as tkFont
from fontTools.ttLib import TTFont
import pickle
from PIL import Image, ImageTk, ImageDraw
import pygame
import os
from io import BytesIO
import tempfile
import sys

class ResourceManager:
    def __init__(self, resources):
        self.resources = resources

class ResourceViewer:
    def __init__(self, root, file_path=None):
        self.root = root
        self.root.title("PFDataViewer")
        self.resource_manager = None
        self.tree = None
        self.text_editor = None
        self.current_file = None
        self.image_label = None
        self.media_frame = None
        self.font_frame = None
        self.unsaved_changes = False
        self.current_resource_key = None
        self.current_tree_item = None
        self.font_cache = {}
        self.content_frame = None
        
        # Image zoom variables
        self.current_image = None
        self.scale_factor = 1.0
        self.image_reference = None

        pygame.init()
        self.create_widgets()
        self.root.geometry("855x400")

        # Bind zoom events
        self.root.bind("<Control-MouseWheel>", self.zoom_image)
        self.content_frame.bind("<Configure>", self.resize_image)

        if file_path:
            self.current_file = file_path
            self.load_resources(file_path)

    def create_widgets(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_exit)
        menubar.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menubar)

        # Main container with paned window
        main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        # Treeview on left
        self.tree = ttk.Treeview(main_pane)
        main_pane.add(self.tree, width=200, minsize=150)

        # Content area on right
        self.content_frame = tk.Frame(main_pane)
        main_pane.add(self.content_frame, minsize=600, stretch='always')

        # Initialize all content widgets
        self.text_editor = scrolledtext.ScrolledText(self.content_frame, wrap=tk.WORD)
        self.image_label = tk.Label(self.content_frame)
        self.media_frame = tk.Frame(self.content_frame)
        self.font_frame = tk.Frame(self.content_frame)
        
        # Font preview setup
        self.font_sample_label = tk.Label(self.font_frame, wraplength=550)
        self.font_sample_label.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Hide all content initially
        self.text_editor.pack_forget()
        self.image_label.pack_forget()
        self.media_frame.pack_forget()
        self.font_frame.pack_forget()

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

    def on_text_change(self, event):
        self.unsaved_changes = True

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("WIN files", "*.win")])
        if file_path:
            self.current_file = file_path
            self.load_resources(file_path)
            self.root.title(f"PFDataViewer [{os.path.basename(file_path)}]")

    def load_resources(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                resources = pickle.load(f)

            manifest = resources.get('!META-INF/MANIFEST', {})
            if manifest:
                manifest = pickle.loads(manifest)

            self.tree.delete(*self.tree.get_children())
            categories = {
                "Fonts": [],
                "Images": [],
                "Rooms": [],
                "Scripts": [],
                "Sounds": []
            }
            for key, value in manifest.items():
                file_name = os.path.basename(key)
                if key.endswith('.ttf'):
                    categories["Fonts"].append((file_name, value))
                elif key.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    categories["Images"].append((file_name, value))
                elif key.endswith('.json'):
                    categories["Rooms"].append((file_name, value))
                elif key.endswith('.py'):
                    categories["Scripts"].append((file_name, value))
                elif key.lower().endswith(('.wav', '.ogg', '.mp3')):
                    categories["Sounds"].append((file_name, value))

            for category in categories:
                category_id = self.tree.insert("", "end", text=category)
                for resource in categories[category]:
                    self.tree.insert(category_id, "end", text=resource[0], values=(resource[1],))

            self.resource_manager = ResourceManager(resources)
            self.unsaved_changes = False

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load resources: {e}")

    def on_tree_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return

        selected_item = selected_items[0]
        key = self.tree.item(selected_item, "text")
        values = self.tree.item(selected_item, "values")
        if not values:
            return

        real_key = values[0]

        if self.current_resource_key and self.current_tree_item:
            parent_id = self.tree.parent(self.current_tree_item)
            if parent_id:
                category = self.tree.item(parent_id, "text")
                if category in ["Scripts", "Rooms"]:
                    new_data = self.text_editor.get("1.0", tk.END).strip().encode('utf-8')
                    current_data = self.resource_manager.resources.get(self.current_resource_key, b'')
                    if new_data != current_data:
                        self.resource_manager.resources[self.current_resource_key] = new_data
                        self.unsaved_changes = True

        self.current_resource_key = real_key
        self.current_tree_item = selected_item

        if self.resource_manager and real_key in self.resource_manager.resources:
            data = self.resource_manager.resources[real_key]
            
            # Hide all content widgets
            self.text_editor.pack_forget()
            self.image_label.pack_forget()
            self.media_frame.pack_forget()
            self.font_frame.pack_forget()

            if isinstance(data, bytes):
                if data.startswith(b'\xff\xd8') or data.startswith(b'\x89PNG'):
                    self.display_image(data)
                    self.image_label.pack(fill=tk.BOTH, expand=True)
                elif data.startswith(b'RIFF') or data.startswith(b'ftyp'):
                    self.play_audio(data)
                    self.media_frame.pack(fill=tk.BOTH, expand=True)
                elif key.lower().endswith('.ttf'):
                    self.display_font(data)
                    self.font_frame.pack(fill=tk.BOTH, expand=True)
                else:
                    try:
                        text_data = data.decode('utf-8')
                        self.text_editor.delete(1.0, tk.END)
                        self.text_editor.insert(tk.END, text_data)
                    except UnicodeDecodeError:
                        hex_data = data.hex()
                        self.text_editor.delete(1.0, tk.END)
                        self.text_editor.insert(tk.END, f"Cannot decode bytes, hex representation:\n{hex_data}")
                    self.text_editor.pack(fill=tk.BOTH, expand=True)
            else:
                self.text_editor.delete(1.0, tk.END)
                self.text_editor.insert(tk.END, str(data))
                self.text_editor.pack(fill=tk.BOTH, expand=True)

            self.text_editor.bind("<KeyRelease>", self.on_text_change)

    def display_font(self, font_data):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ttf') as temp_file:
                temp_file.write(font_data)
                temp_font_path = temp_file.name
            
            tt = TTFont(temp_font_path)
            name_records = tt['name'].names
            font_family = "Unknown Font"
            
            for record in name_records:
                if record.nameID == 1 and not font_family:
                    font_family = record.toUnicode()
                    break
            
            tt.close()

            try:
                from PIL import ImageFont
                pil_font = ImageFont.truetype(temp_font_path, 20)
                
                sample_text = (
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZ\n"
                    "abcdefghijklmnopqrstuvwxyz\n"
                    "1234567890\n"
                    "!@#$%^&*()_+-=[]{}|;:'\",.<>/?`~"
                )

                img = Image.new('RGB', (550, 300), color=(255, 255, 255))
                draw = ImageDraw.Draw(img)
                draw.text((10, 10), sample_text, font=pil_font, fill=(0, 0, 0))
                
                photo = ImageTk.PhotoImage(img)
                self.font_sample_label.config(image=photo)
                self.font_sample_label.image = photo
                
            except Exception as e:
                self.font_sample_label.config(
                    text=f"Error loading font: {str(e)}",
                    font=("Arial", 12)
                )

            self.font_cache[font_family] = {
                'path': temp_font_path,
                'font': temp_font_path
            }

        except Exception as e:
            self.font_sample_label.config(
                text=f"Error loading font: {str(e)}",
                font=("Arial", 12)
            )

    def on_double_click(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return

        selected_item = selected_items[0]
        values = self.tree.item(selected_item, "values")
        if not values:
            return

        real_key = values[0]

        if self.resource_manager and real_key in self.resource_manager.resources:
            export_window = tk.Toplevel(self.root)
            export_window.title("Export Resource")
            export_window.geometry("300x100")

            export_button = tk.Button(
                export_window, 
                text="Export Resource", 
                command=lambda: self.export_resource(real_key)
            )
            export_button.pack(pady=20)

    def export_resource(self, resource_key):
        if self.resource_manager and resource_key in self.resource_manager.resources:
            data = self.resource_manager.resources[resource_key]
            file_name = os.path.basename(resource_key)

            save_path = filedialog.asksaveasfilename(
                defaultextension=os.path.splitext(file_name)[1], 
                filetypes=[("All Files", "*.*")], 
                initialfile=file_name
            )
            if save_path:
                try:
                    with open(save_path, 'wb') as f:
                        f.write(data)
                    messagebox.showinfo("Success", f"Resource saved to {save_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save resource: {e}")

    def display_image(self, data):
        image_data = BytesIO(data)
        try:
            self.current_image = Image.open(image_data)
            self.scale_factor = 1.0
            self.update_image()
            self.image_label.pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to display image: {e}")

    def zoom_image(self, event):
        if self.current_image is None:
            return

        # Zoom factor
        zoom_rate = 1.1
        if event.delta > 0:
            self.scale_factor *= zoom_rate
        else:
            self.scale_factor /= zoom_rate

        # Limit zoom range
        self.scale_factor = max(0.1, min(self.scale_factor, 5.0))
        
        self.update_image()

    def update_image(self, event=None):
        if self.current_image is None:
            return

        # Calculate new size
        width = int(self.current_image.width * self.scale_factor)
        height = int(self.current_image.height * self.scale_factor)
        
        # Resize image
        resized_image = self.current_image.resize(
            (width, height),
            Image.Resampling.LANCZOS
        )
        
        # Update image label
        self.image_reference = ImageTk.PhotoImage(resized_image)
        self.image_label.config(image=self.image_reference)

    def resize_image(self, event=None):
        if self.current_image and self.scale_factor == 1.0:
            content_width = self.content_frame.winfo_width() - 20
            content_height = self.content_frame.winfo_height() - 20
            
            # Calculate aspect ratio
            img_ratio = self.current_image.width / self.current_image.height
            frame_ratio = content_width / content_height
            
            if img_ratio > frame_ratio:
                new_width = content_width
                new_height = int(new_width / img_ratio)
            else:
                new_height = content_height
                new_width = int(new_height * img_ratio)
            
            self.scale_factor = min(new_width/self.current_image.width, new_height/self.current_image.height)
            self.update_image()

    def play_audio(self, data):
        try:
            for widget in self.media_frame.winfo_children():
                widget.destroy()

            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(data)
                temp_file_path = temp_file.name

            play_button = tk.Button(
                self.media_frame, 
                text="Play Audio", 
                command=lambda: pygame.mixer.music.load(temp_file_path) or pygame.mixer.music.play()
            )
            stop_button = tk.Button(
                self.media_frame,
                text="Stop Audio",
                command=pygame.mixer.music.stop
            )
            
            play_button.pack(side=tk.LEFT, padx=5)
            stop_button.pack(side=tk.LEFT, padx=150)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to play audio: {e}")

    def save_file(self):
        if self.current_file and self.resource_manager:
            if self.current_tree_item:
                parent_id = self.tree.parent(self.current_tree_item)
                if parent_id:
                    category = self.tree.item(parent_id, "text")
                    if category in ["Scripts", "Rooms"]:
                        new_data = self.text_editor.get("1.0", tk.END).strip().encode('utf-8')
                        self.resource_manager.resources[self.current_resource_key] = new_data

            try:
                with open(self.current_file, 'wb') as f:
                    pickle.dump(self.resource_manager.resources, f)
                messagebox.showinfo("Success", "File saved successfully")
                self.unsaved_changes = False
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")

    def on_exit(self):
        for font_info in self.font_cache.values():
            try:
                if os.path.exists(font_info['path']):
                    os.remove(font_info['path'])
            except Exception as e:
                print(f"Error cleaning font cache: {e}")
                
        if self.unsaved_changes:
            response = messagebox.askyesnocancel("Save Changes", "Do you want to save changes before exiting?")
            if response is None:
                return
            elif response:
                self.save_file()
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()

    file_path = None
    if len(sys.argv) > 1:
        file_path = sys.argv[1]

    app = ResourceViewer(root, file_path)

    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    ico_file = os.path.join(base_path, "res", "gear_icon-70125.ico")
    try:
        root.iconbitmap(ico_file)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to set icon: {e}")

    root.mainloop()