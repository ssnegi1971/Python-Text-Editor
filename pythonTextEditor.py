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
        
        # Configure a highlight tag for found text
        self.text_edit.tag_configure("match", background="yellow", foreground="black")
        
        text_scrollbar = ttk.Scrollbar(text_container, orient=tk.VERTICAL, command=self.text_edit.yview)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_list.config(yscrollcommand=list_scrollbar.set)
        self.text_edit.config(yscrollcommand=text_scrollbar.set)
        
        # Control row container for workflow action shortcuts
        button_row = ttk.Frame(right_frame)
        button_row.pack(fill=tk.X, pady=(5, 0))
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)
        button_row.columnconfigure(2, weight=1)
        button_row.columnconfigure(3, weight=1)
        
        self.new_btn = ttk.Button(button_row, text="📄 New File", command=self.new_file)
        self.new_btn.grid(row=0, column=0, padx=(0, 2), sticky="ew")

        self.save_btn = ttk.Button(button_row, text="💾 Save File", command=self.save_file)
        self.save_btn.grid(row=0, column=1, padx=2, sticky="ew")
        
        self.find_btn = ttk.Button(button_row, text="🔍 Find & Replace", command=self.open_find_dialog)
        self.find_btn.grid(row=0, column=2, padx=2, sticky="ew")
        
        self.close_file_btn = ttk.Button(button_row, text="🔒 Close File", command=self.close_file)
        self.close_file_btn.grid(row=0, column=3, padx=(2, 0), sticky="ew")
        
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
            
    def new_file(self):
        """Clears the workspace and unlinks any existing active tracking paths."""
        self.current_file_path = ""
        self.text_edit.tag_remove("match", "1.0", tk.END)
        self.text_edit.delete("1.0", tk.END)
        self.file_list.selection_clear(0, tk.END)
        self.text_edit.focus_set()

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
            
    def open_find_dialog(self):
        """Opens a custom popup window to search and replace text inside the editor window."""
        find_dialog = tk.Toplevel(self.root)
        find_dialog.title("Find & Replace")
        find_dialog.geometry("400x180")
        find_dialog.resizable(False, False)
        find_dialog.transient(self.root)
        
        # Grid Configuration for clean layout alignment
        find_dialog.columnconfigure(1, weight=1)
        
        # Find Field
        lbl_find = ttk.Label(find_dialog, text="Find text:")
        lbl_find.grid(row=0, column=0, padx=10, pady=(15, 5), sticky="w")
        entry_find = ttk.Entry(find_dialog, width=30)
        entry_find.grid(row=0, column=1, padx=10, pady=(15, 5), sticky="ew")
        entry_find.focus_set()
        
        # Replace Field
        lbl_replace = ttk.Label(find_dialog, text="Replace with:")
        lbl_replace.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        entry_replace = ttk.Entry(find_dialog, width=30)
        entry_replace.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        def highlight_matches():
            self.text_edit.tag_remove("match", "1.0", tk.END)
            search_query = entry_find.get()
            if not search_query:
                return 0
                
            start_pos = "1.0"
            count = 0
            while True:
                start_pos = self.text_edit.search(search_query, start_pos, stopindex=tk.END)
                if not start_pos:
                    break
                end_pos = f"{start_pos}+{len(search_query)}c"
                self.text_edit.tag_add("match", start_pos, end_pos)
                if count == 0:
                    self.text_edit.see(start_pos)
                start_pos = end_pos
                count += 1
            return count
        def replace_one():
            search_query = entry_find.get()
            replace_query = entry_replace.get()
            if not search_query:
                return
                
            # Search from the current insert cursor spot, or fallback to the beginning
            start_pos = self.text_edit.index(tk.INSERT)
            pos = self.text_edit.search(search_query, start_pos, stopindex=tk.END)
            
            # Loop back to top if not found from cursor position downwards
            if not pos:
                pos = self.text_edit.search(search_query, "1.0", stopindex=tk.END)
                
            if pos:
                end_pos = f"{pos}+{len(search_query)}c"
                self.text_edit.delete(pos, end_pos)
                self.text_edit.insert(pos, replace_query)
                # Move cursor right after the newly inserted term
                new_end_pos = f"{pos}+{len(replace_query)}c"
                self.text_edit.mark_set(tk.INSERT, new_end_pos)
                self.text_edit.see(new_end_pos)
                highlight_matches()
            else:
                messagebox.showinfo("Replace", "No occurrences found.", parent=find_dialog)
        def replace_all():
            search_query = entry_find.get()
            replace_query = entry_replace.get()
            if not search_query:
                return
                
            start_pos = "1.0"
            count = 0
            # Disable undo stacking temporarily to group everything into a single action sequence
            self.text_edit.config(autoseparators=False)
            
            while True:
                pos = self.text_edit.search(search_query, start_pos, stopindex=tk.END)
                if not pos:
                    break
                end_pos = f"{pos}+{len(search_query)}c"
                self.text_edit.delete(pos, end_pos)
                self.text_edit.insert(pos, replace_query)
                start_pos = f"{pos}+{len(replace_query)}c"
                count += 1
                
            self.text_edit.config(autoseparators=True)
            self.text_edit.tag_remove("match", "1.0", tk.END)
            
            if count > 0:
                messagebox.showinfo("Replace All", f"Successfully replaced {count} occurrence(s).", parent=find_dialog)
            else:
                messagebox.showinfo("Replace All", "No occurrences found.", parent=find_dialog)
        # Button row container within the popup layout framework
        btn_frame = ttk.Frame(find_dialog)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=15, sticky="ew")
        btn_frame.columnconfigure((0, 1, 2), weight=1)
        
        btn_find = ttk.Button(btn_frame, text="Find/Highlight", command=highlight_matches)
        btn_find.grid(row=0, column=0, padx=5)
        
        btn_rep_one = ttk.Button(btn_frame, text="Replace One", command=replace_one)
        btn_rep_one.grid(row=0, column=1, padx=5)
        
        btn_rep_all = ttk.Button(btn_frame, text="Replace All", command=replace_all)
        btn_rep_all.grid(row=0, column=2, padx=5)
        
        # Trigger highlights on interactive keystroke typing updates
        entry_find.bind("<KeyRelease>", lambda e: highlight_matches())
    def close_file(self):
        """Clears the active workspace text frame and drops tracking path details."""
        self.current_file_path = ""
        self.text_edit.tag_remove("match", "1.0", tk.END)
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
