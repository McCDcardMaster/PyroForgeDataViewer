import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pickle
from PIL import Image, ImageTk
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
        self.unsaved_changes = False
        self.current_resource_key = None
        self.current_tree_item = None

        pygame.init()
        self.create_widgets()

        # Если передан путь к файлу, загружаем его
        if file_path:
            self.current_file = file_path
            self.load_resources(file_path)

    def create_widgets(self):
        # Menu
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_exit)
        menubar.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menubar)

        self.tree = ttk.Treeview(self.root)
        self.tree.pack(side=tk.LEFT, fill=tk.Y)
        self.text_editor = scrolledtext.ScrolledText(self.root, wrap=tk.WORD)
        self.text_editor.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.text_editor.bind("<KeyRelease>", self.on_text_change)

        self.image_label = tk.Label(self.root)
        self.image_label.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        self.media_frame = tk.Frame(self.root)
        self.media_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", self.on_double_click)


        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

    def on_text_change(self, event):
        """Обработчик изменения текста в текстовом редакторе."""
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

        if self.current_resource_key is not None and self.current_tree_item is not None:
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
            self.text_editor.unbind("<KeyRelease>")
            self.text_editor.delete(1.0, tk.END)
            self.image_label.config(image='')
            for widget in self.media_frame.winfo_children():
                widget.destroy()

            if isinstance(data, bytes):
                if data.startswith(b'\xff\xd8') or data.startswith(b'\x89PNG'):
                    self.display_image(data)
                elif data.startswith(b'RIFF') or data.startswith(b'ftyp'):
                    self.play_audio(data)
                else:
                    try:
                        text_data = data.decode('utf-8')
                        self.text_editor.insert(tk.END, text_data)
                    except UnicodeDecodeError:
                        hex_data = data.hex()
                        self.text_editor.insert(tk.END, f"Cannot decode bytes, hex representation:\n{hex_data}")
            else:
                self.text_editor.insert(tk.END, str(data))

            self.text_editor.bind("<KeyRelease>", self.on_text_change)

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

            export_button = tk.Button(export_window, text="Export Resource", command=lambda: self.export_resource(real_key))
            export_button.pack(pady=20)

    def export_resource(self, resource_key):
        """Выгружает ресурс в выбранную пользователем папку."""
        if self.resource_manager and resource_key in self.resource_manager.resources:
            data = self.resource_manager.resources[resource_key]
            file_name = os.path.basename(resource_key)

            save_path = filedialog.asksaveasfilename(defaultextension=os.path.splitext(file_name)[1], filetypes=[("All Files", "*.*")], initialfile=file_name)
            if save_path:
                try:
                    with open(save_path, 'wb') as f:
                        f.write(data)
                    messagebox.showinfo("Success", f"Resource saved to {save_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save resource: {e}")

    def set_font(self, font_key):
        if font_key in self.resource_manager.resources:
            font_data = self.resource_manager.resources[font_key]
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ttf') as temp_font_file:
                temp_font_file.write(font_data)
                temp_font_path = temp_font_file.name
            try:
                self.text_editor.config(font=(temp_font_path, 12))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load font: {e}")

    def display_image(self, data):
        image_data = BytesIO(data)
        image = Image.open(image_data)
        image.thumbnail((400, 400))
        photo = ImageTk.PhotoImage(image)
        self.image_label.config(image=photo)
        self.image_label.image = photo

    def play_audio(self, data):
        try:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(data)
                temp_file_path = temp_file.name

            pygame.mixer.music.load(temp_file_path)
            pygame.mixer.music.play()
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
