import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class TextEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Tkinter Text Editor")
        self.root.geometry("1000x600")
        
        self.current_directory = ""
        self.current_file_path = ""
        
        self.init_ui()

    def init_ui(self):
        # Configure layout weights for responsive window resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Use a PanedWindow to allow users to drag and resize the side columns
        paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned_window.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # --- Left Pane (Directory Browsing & File List) ---
        left_frame = ttk.Frame(paned_window, padding=5)
        
        self.browse_btn = ttk.Button(left_frame, text="📂 Browse Directory", command=self.browse_directory)
        self.browse_btn.pack(fill=tk.X, pady=(0, 5))
        
        # Listbox for filenames paired with a vertical scrollbar
        list_container = ttk.Frame(left_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        self.file_list = tk.Listbox(list_container, selectmode=tk.SINGLE, exportselection=False)
        self.file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.file_list.bind('<<ListboxSelect>>', self.load_file)
        
        list_scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.file_list.yview)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_list.config(yscrollcommand=list_scrollbar.set)
        
        # Button to reset directory path tracking completely
        self.close_all_btn = ttk.Button(left_frame, text="❌ Close All Files", command=self.close_all_files)
        self.close_all_btn.pack(fill=tk.X, pady=(5, 0))
        
        # --- Right Pane (Text Editor Area) ---
        right_frame = ttk.Frame(paned_window, padding=5)
        
        # Text editing widget paired with a vertical scrollbar
        text_container = ttk.Frame(right_frame)
        text_container.pack(fill=tk.BOTH, expand=True)
        
        self.text_edit = tk.Text(text_container, wrap=tk.WORD, undo=True)
        self.text_edit.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        text_scrollbar = ttk.Scrollbar(text_container, orient=tk.VERTICAL, command=self.text_edit.yview)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_edit.config(yscrollcommand=text_scrollbar.set)
        
        # Control row container for workflow action shortcuts
        button_row = ttk.Frame(right_frame)
        button_row.pack(fill=tk.X, pady=(5, 0))
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)
        
        self.save_btn = ttk.Button(button_row, text="💾 Save File", command=self.save_file)
        self.save_btn.grid(row=0, column=0, padx=(0, 2), sticky="ew")
        
        self.close_file_btn = ttk.Button(button_row, text="🔒 Close File", command=self.close_file)
        self.close_file_btn.grid(row=0, column=1, padx=(2, 0), sticky="ew")
        
        # Pack layouts into the split window panes
        paned_window.add(left_frame, weight=1)
        paned_window.add(right_frame, weight=3)

    def browse_directory(self):
        directory = filedialog.askdirectory(title="Select Folder")
        if directory:
            self.current_directory = directory
            self.refresh_file_list()

    def refresh_file_list(self):
        self.file_list.delete(0, tk.END)
        try:
            # Gather files from directory
            all_items = os.listdir(self.current_directory)
            
            # Filter to show ONLY files that end with a .txt extension
            files_only = [
                f for f in all_items 
                if os.path.isfile(os.path.join(self.current_directory, f)) 
                and f.lower().endswith('.txt')
            ]
            
            # Populate sorted text files into the Left Pane
            for file in sorted(files_only):
                self.file_list.insert(tk.END, file)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load directory files:\n{str(e)}")

    def load_file(self, event):
        # Ignore event firings when selection is empty
        selection = self.file_list.curselection()
        if not selection:
            return
            
        filename = self.file_list.get(selection)
        self.current_file_path = os.path.join(self.current_directory, filename)
        
        try:
            with open(self.current_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Clear editor contents and insert the file text
            self.text_edit.delete("1.0", tk.END)
            self.text_edit.insert("1.0", content)
        except Exception as e:
            messagebox.showerror("Error", f"Could not read file:\n{str(e)}")

    def save_file(self):
        # Fallback mechanism: trigger 'Save As' if no file was loaded first
        if not self.current_file_path:
            file_path = filedialog.asksaveasfilename(
                initialdir=self.current_directory,
                title="Save File As",
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
            )
            if file_path:
                self.current_file_path = file_path
            else:
                return

        try:
            # Extract content from line 1 character 0, up to the end of the text widget
            content = self.text_edit.get("1.0", tk.END)
            
            with open(self.current_file_path, 'w', encoding='utf-8') as f:
                f.write(content.rstrip('\n') + '\n')
                
            messagebox.showinfo("Saved", "File saved successfully!")
            self.refresh_file_list()
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file:\n{str(e)}")

    def close_file(self):
        """Clears the active workspace text frame and drops tracking path details."""
        self.current_file_path = ""
        self.text_edit.delete("1.0", tk.END)
        self.file_list.selection_clear(0, tk.END)

    def close_all_files(self):
        """Wipes out both the text editor tracking and clears the sidebar folder view."""
        self.close_file()
        self.current_directory = ""
        self.file_list.delete(0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = TextEditorApp(root)
    root.mainloop()
