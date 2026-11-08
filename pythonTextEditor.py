import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

class TextEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Tkinter Text Editor")
        self.root.geometry("1100x600")
        
        self.current_directory = ""
        self.current_file_path = ""
        self.untitled_count = 0  
        
        self.workspace_cache = {}
        self.last_selected_item = None
        
        self.init_ui()
        
    def init_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned_window.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # --- Left Pane ---
        left_frame = ttk.Frame(paned_window, padding=5)
        
        self.browse_btn = ttk.Button(left_frame, text="📂 Browse Directory", command=self.browse_directory)
        self.browse_btn.pack(fill=tk.X, pady=(0, 5))
        
        list_container = ttk.Frame(left_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        self.file_list = tk.Listbox(list_container, selectmode=tk.SINGLE, exportselection=False)
        self.file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.file_list.bind('<<ListboxSelect>>', self.load_file)
        self.file_list.bind('<Button-1>', self.check_remove_click)
        
        list_scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.file_list.yview)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_list.config(yscrollcommand=list_scrollbar.set)
        
        self.close_all_btn = ttk.Button(left_frame, text="❌ Close All Files", command=self.close_all_files)
        self.close_all_btn.pack(fill=tk.X, pady=(5, 0))
        
        # --- Right Pane ---
        right_frame = ttk.Frame(paned_window, padding=5)
        
        # Text editing frame containing ruler and text area side-by-side
        text_layout_frame = ttk.Frame(right_frame)
        text_layout_frame.pack(fill=tk.BOTH, expand=True)
        
        # Line count ruler (Canvas widget)
        self.line_ruler = tk.Canvas(text_layout_frame, width=45, bg="#f0f0f0", bd=0, highlightthickness=0)
        self.line_ruler.pack(side=tk.LEFT, fill=tk.Y)
        
        # Text editing widget
        self.text_edit = tk.Text(text_layout_frame, wrap=tk.WORD, undo=True)
        self.text_edit.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text_edit.tag_configure("match", background="yellow", foreground="black")
        
        # Scrollbar linked to text component
        text_scrollbar = ttk.Scrollbar(text_layout_frame, orient=tk.VERTICAL, command=self.text_edit.yview)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_edit.config(yscrollcommand=text_scrollbar.set)
        
        # Triggers to update the line count ruler dynamically
        self.text_edit.bind('<KeyRelease>', self.update_line_ruler)
        self.text_edit.bind('<ButtonRelease-1>', self.update_line_ruler)
        self.text_edit.bind('<MouseWheel>', self.update_line_ruler)
        self.text_edit.bind('<Configure>', self.update_line_ruler)
        # For Linux scroll events
        self.text_edit.bind('<Button-4>', self.update_line_ruler)
        self.text_edit.bind('<Button-5>', self.update_line_ruler)
        
        # Custom scroll command proxy to capture scrollbar drag movements
        def on_scroll(*args):
            text_scrollbar.set(*args)
            self.update_line_ruler()
        self.text_edit.config(yscrollcommand=on_scroll)
        
        # Control row container for workflow action shortcuts
        button_row = ttk.Frame(right_frame)
        button_row.pack(fill=tk.X, pady=(5, 0))
        button_row.columnconfigure((0, 1, 2, 3, 4), weight=1)
        
        self.new_btn = ttk.Button(button_row, text="📄 New File", command=self.new_file)
        self.new_btn.grid(row=0, column=0, padx=(0, 2), sticky="ew")
        
        self.save_btn = ttk.Button(button_row, text="💾 Save File", command=self.save_file)
        self.save_btn.grid(row=0, column=1, padx=2, sticky="ew")
        
        self.find_btn = ttk.Button(button_row, text="🔍 Find & Replace", command=self.open_find_dialog)
        self.find_btn.grid(row=0, column=2, padx=2, sticky="ew")
        
        self.goto_btn = ttk.Button(button_row, text="➡️ Goto Line", command=self.goto_line)
        self.goto_btn.grid(row=0, column=3, padx=2, sticky="ew")
        
        self.close_file_btn = ttk.Button(button_row, text="🔒 Close File", command=self.close_file)
        self.close_file_btn.grid(row=0, column=4, padx=(2, 0), sticky="ew")
        
        paned_window.add(left_frame, weight=1)
        paned_window.add(right_frame, weight=3)
        
        # Initialize ruler on startup
        self.update_line_ruler()
        
    def update_line_ruler(self, event=None):
        '''Redraws the numerical line indicators inside the canvas ruler panel alignment.'''
        self.line_ruler.delete("all")
        
        # Iterate over text rows visually present in the viewport
        i = self.text_edit.index("@0,0")
        while True:
            dline = self.text_edit.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            line_num = i.split(".")[0]
            # Draw line number slightly offset from the right boundary edge
            self.line_ruler.create_text(38, y, anchor="ne", text=line_num, fill="#666666", font=("Courier", 10))
            i = self.text_edit.index(f"{i}+1line")
            
    def goto_line(self):
        '''Prompts user to navigate directly to a target line row index row line.'''
        # Calculate maximum current rows
        total_lines = int(self.text_edit.index('end-1c').split('.')[0])
        
        line_num = simpledialog.askinteger(
            "Goto Line", 
            f"Enter line number (1-{total_lines}):", 
            parent=self.root,
            minvalue=1, 
            maxvalue=total_lines
        )
        
        if line_num:
            # Set cursor focus to target index point position
            self.text_edit.mark_set(tk.INSERT, f"{line_num}.0")
            self.text_edit.see(f"{line_num}.0")
            self.text_edit.focus_set()
            self.update_line_ruler()
            
    def browse_directory(self):
        directory = filedialog.askdirectory(title="Select Folder")
        if directory:
            self.current_directory = directory
            self.workspace_cache.clear()
            self.last_selected_item = None
            self.refresh_file_list()
            
    def refresh_file_list(self):
        temp_untitleds = [item for item in self.file_list.get(0, tk.END) if item.startswith("Untitled-")]
        self.file_list.delete(0, tk.END)
        try:
            if self.current_directory:
                all_items = os.listdir(self.current_directory)
                files_only = [
                    f for f in all_items 
                    if os.path.isfile(os.path.join(self.current_directory, f)) 
                    and f.lower().endswith('.txt')
                ]
                for file in sorted(files_only):
                    self.file_list.insert(tk.END, f"{file}  ❌")
            for unt in temp_untitleds:
                self.file_list.insert(tk.END, unt)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load directory files:\n{str(e)}")
            
    def save_current_to_cache(self):
        if self.last_selected_item:
            current_content = self.text_edit.get("1.0", tk.END)
            self.workspace_cache[self.last_selected_item] = current_content

    def load_file(self, event=None):
        selection = self.file_list.curselection()
        if not selection:
            return
            
        display_name = self.file_list.get(selection)
        
        self.save_current_to_cache()
        self.last_selected_item = display_name
        self.text_edit.tag_remove("match", "1.0", tk.END)
        
        if display_name.startswith("Untitled-"):
            self.current_file_path = ""
            self.text_edit.delete("1.0", tk.END)
            if display_name in self.workspace_cache:
                self.text_edit.insert("1.0", self.workspace_cache[display_name])
            self.root.after(10, self.update_line_ruler)
            return
            
        filename = display_name.removesuffix("  ❌")
        self.current_file_path = os.path.join(self.current_directory, filename)
        
        if display_name in self.workspace_cache:
            self.text_edit.delete("1.0", tk.END)
            self.text_edit.insert("1.0", self.workspace_cache[display_name])
            self.root.after(10, self.update_line_ruler)
            return
            
        try:
            if os.path.exists(self.current_file_path):
                with open(self.current_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                self.text_edit.delete("1.0", tk.END)
                self.text_edit.insert("1.0", content)
            else:
                messagebox.showerror("Error", f"File path does not exist:\n{self.current_file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not read file:\n{str(e)}")
        finally:
            self.root.after(10, self.update_line_ruler)
            
    def check_remove_click(self, event):
        index = self.file_list.nearest(event.y)
        if index < 0:
            return
            
        bbox = self.file_list.bbox(index)
        if not bbox:
            return
            
        x_start, y_start, width, height = bbox
        
        if event.x > (x_start + width - 30):
            display_name = self.file_list.get(index)
            filename = display_name.removesuffix("  ❌")
            
            if display_name in self.workspace_cache:
                del self.workspace_cache[display_name]
                
            if self.last_selected_item == display_name:
                self.last_selected_item = None
                self.close_file()
            
            if not display_name.startswith("Untitled-"):
                target_path = os.path.join(self.current_directory, filename)
                if self.current_file_path == target_path:
                    self.close_file()
                    
            self.file_list.delete(index)
            return "break"
            
    def new_file(self):
        self.save_current_to_cache()
        
        self.current_file_path = ""
        self.text_edit.tag_remove("match", "1.0", tk.END)
        self.text_edit.delete("1.0", tk.END)
        self.file_list.selection_clear(0, tk.END)
        
        self.untitled_count += 1
        placeholder_name = f"Untitled-{self.untitled_count}  ❌"
        
        self.workspace_cache[placeholder_name] = ""
        self.file_list.insert(tk.END, placeholder_name)
        
        new_idx = self.file_list.size() - 1
        self.file_list.selection_set(new_idx)
        self.file_list.activate(new_idx)
        self.last_selected_item = placeholder_name
        self.text_edit.focus_set()
        self.update_line_ruler()
        
    def save_file(self):
        if not self.current_file_path:
            file_path = filedialog.asksaveasfilename(
                initialdir=self.current_directory if self.current_directory else os.path.expanduser("~"),
                title="Save File As",
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
            )
            if file_path:
                self.current_file_path = file_path
                selection = self.file_list.curselection()
                if selection:
                    display_name = self.file_list.get(selection)
                    if display_name in self.workspace_cache:
                        del self.workspace_cache[display_name]
                    if display_name.startswith("Untitled-"):
                        self.file_list.delete(selection)
                self.current_directory = os.path.dirname(file_path)
            else:
                return
        try:
            content = self.text_edit.get("1.0", tk.END)
            with open(self.current_file_path, 'w', encoding='utf-8') as f:
                f.write(content.rstrip('\n') + '\n')
                
            messagebox.showinfo("Saved", "File saved successfully!")
            
            saved_display_name = os.path.basename(self.current_file_path) + "  ❌"
            if saved_display_name in self.workspace_cache:
                del self.workspace_cache[saved_display_name]
                
            self.refresh_file_list()
            
            items = self.file_list.get(0, tk.END)
            if saved_display_name in items:
                idx = items.index(saved_display_name)
                self.file_list.selection_set(idx)
                self.last_selected_item = saved_display_name
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file:\n{str(e)}")
        finally:
            self.update_line_ruler()
            
    def open_find_dialog(self):
        find_dialog = tk.Toplevel(self.root)
        find_dialog.title("Find & Replace")
        find_dialog.geometry("400x180")
        find_dialog.resizable(False, False)
        find_dialog.transient(self.root)
        find_dialog.columnconfigure(1, weight=1)
        lbl_find = ttk.Label(find_dialog, text="Find text:")
        lbl_find.grid(row=0, column=0, padx=10, pady=(15, 5), sticky="w")
        entry_find = ttk.Entry(find_dialog, width=30)
        entry_find.grid(row=0, column=1, padx=10, pady=(15, 5), sticky="ew")
        entry_find.focus_set()
        
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
                
            start_pos = self.text_edit.index(tk.INSERT)
            pos = self.text_edit.search(search_query, start_pos, stopindex=tk.END)
            if not pos:
                pos = self.text_edit.search(search_query, "1.0", stopindex=tk.END)
                
            if pos:
                end_pos = f"{pos}+{len(search_query)}c"
                self.text_edit.delete(pos, end_pos)
                self.text_edit.insert(pos, replace_query)
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
                
        btn_frame = ttk.Frame(find_dialog)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=15, sticky="ew")
        btn_frame.columnconfigure((0, 1, 2), weight=1)
        
        btn_find = ttk.Button(btn_frame, text="Find/Highlight", command=highlight_matches)
        btn_find.grid(row=0, column=0, padx=5)
        btn_rep_one = ttk.Button(btn_frame, text="Replace One", command=replace_one)
        btn_rep_one.grid(row=0, column=1, padx=5)
        btn_rep_all = ttk.Button(btn_frame, text="Replace All", command=replace_all)
        btn_rep_all.grid(row=0, column=2, padx=5)
        
        entry_find.bind("<KeyRelease>", lambda e: highlight_matches())
        
    def close_file(self):
        if self.last_selected_item in self.workspace_cache:
            del self.workspace_cache[self.last_selected_item]
        self.last_selected_item = None
        self.current_file_path = ""
        self.text_edit.tag_remove("match", "1.0", tk.END)
        self.text_edit.delete("1.0", tk.END)
        self.file_list.selection_clear(0, tk.END)
        self.update_line_ruler()
        
    def close_all_files(self):
        self.workspace_cache.clear()
        self.last_selected_item = None
        self.current_file_path = ""
        self.text_edit.tag_remove("match", "1.0", tk.END)
        self.text_edit.delete("1.0", tk.END)
        self.current_directory = ""
        self.file_list.delete(0, tk.END)
        self.update_line_ruler()

if __name__ == "__main__":
    root = tk.Tk()
    app = TextEditorApp(root)
    root.mainloop()
