import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import sys
import os
import json
from datetime import datetime
import tempfile

# Add the current directory to the path to import the SQL compiler modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from sql_compiler import SQLGenerator
    from database import Database
except ImportError as e:
    print(f"Error importing SQL compiler modules: {e}")
    sys.exit(1)

class SQLCompilerUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SQL Compiler")
        self.root.geometry("1000x700")
        
        # Initialize database and compiler
        self.db = Database()
        # Don't initialize another SQLCompilerUI instance here
        self.compiler =  SQLGenerator(self.db)
        
        # Query history
        self.history = []
        
        # Create the UI components
        self.create_menu()
        self.create_ui()
        
        # Set theme colors
        self.set_theme()
        
    def set_theme(self):
        # Configure ttk styles
        style = ttk.Style()
        style.configure("TButton", padding=6, relief="flat", background="#4CAF50")
        style.configure("Execute.TButton", background="#4CAF50", foreground="white")
        style.configure("TNotebook", background="#f0f0f0")
        style.configure("TNotebook.Tab", padding=[12, 4], font=('Arial', 10))
        
    def create_menu(self):
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Query", command=self.new_query)
        file_menu.add_command(label="Open Query...", command=self.open_query)
        file_menu.add_command(label="Save Query...", command=self.save_query)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Clear Editor", command=self.clear_editor)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)
    
    def create_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title and description
        title_label = ttk.Label(main_frame, text="SQL Compiler", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 5), anchor=tk.W)
        
        description_label = ttk.Label(
            main_frame, 
            text="Write and execute SQL queries with real-time results visualization.",
            font=("Arial", 10)
        )
        description_label.pack(pady=(0, 10), anchor=tk.W)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 5))
        
        execute_button = ttk.Button(
            button_frame, 
            text="Execute", 
            command=self.execute_query,
            style="Execute.TButton"
        )
        execute_button.pack(side=tk.LEFT, padx=(0, 5))
        
        clear_button = ttk.Button(
            button_frame, 
            text="Clear", 
            command=self.clear_editor
        )
        clear_button.pack(side=tk.LEFT, padx=(0, 5))
        
        save_button = ttk.Button(
            button_frame, 
            text="Save", 
            command=self.save_query
        )
        save_button.pack(side=tk.LEFT, padx=(0, 5))
        
        load_button = ttk.Button(
            button_frame, 
            text="Load", 
            command=self.open_query
        )
        load_button.pack(side=tk.LEFT)
        
        # Query editor
        editor_frame = ttk.LabelFrame(main_frame, text="SQL Query")
        editor_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.query_editor = scrolledtext.ScrolledText(
            editor_frame, 
            wrap=tk.WORD,
            width=40, 
            height=10,
            font=("Consolas", 11)
        )
        self.query_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Default query
        self.query_editor.insert(tk.END, "SELECT * FROM users LIMIT 10;")
        
        # Configure tags for syntax highlighting
        self.query_editor.tag_configure("keyword", foreground="#0033CC", font=("Consolas", 11, "bold"))
        self.query_editor.tag_configure("function", foreground="#CC00CC", font=("Consolas", 11))
        self.query_editor.tag_configure("string", foreground="#009900")
        self.query_editor.tag_configure("number", foreground="#FF6600")
        self.query_editor.tag_configure("comment", foreground="#999999", font=("Consolas", 11, "italic"))
        
        # Bind events for syntax highlighting
        self.query_editor.bind("<KeyRelease>", self.highlight_syntax)
        
        # Results notebook (tabs)
        self.results_notebook = ttk.Notebook(main_frame)
        self.results_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Results tab
        self.results_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.results_frame, text="Results")
        
        # Create a frame for the results table
        self.table_frame = ttk.Frame(self.results_frame)
        self.table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Initial message
        self.initial_message = ttk.Label(
            self.table_frame, 
            text="Execute a query to see results",
            font=("Arial", 11),
            foreground="#666666"
        )
        self.initial_message.pack(expand=True)
        
        # History tab
        self.history_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.history_frame, text="History")
        
        # Create history list
        self.history_list = tk.Listbox(
            self.history_frame,
            font=("Consolas", 10),
            activestyle="none",
            selectbackground="#e0e0e0",
            selectforeground="#000000"
        )
        self.history_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar for history list
        history_scrollbar = ttk.Scrollbar(self.history_frame, orient=tk.VERTICAL, command=self.history_list.yview)
        history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_list.config(yscrollcommand=history_scrollbar.set)
        
        # Bind double-click on history item
        self.history_list.bind("<Double-Button-1>", self.load_from_history)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(
            self.root, 
            textvariable=self.status_var, 
            relief=tk.SUNKEN, 
            anchor=tk.W
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def highlight_syntax(self, event=None):
        # Clear all tags
        for tag in ["keyword", "function", "string", "number", "comment"]:
            self.query_editor.tag_remove(tag, "1.0", tk.END)
        
        # SQL keywords
        keywords = [
            "SELECT", "FROM", "WHERE", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "TABLE",
            "INTO", "VALUES", "SET", "AND", "OR", "NOT", "NULL", "IS", "IN", "LIKE", "BETWEEN",
            "JOIN", "INNER", "LEFT", "RIGHT", "OUTER", "ON", "GROUP", "BY", "HAVING", "ORDER",
            "ASC", "DESC", "LIMIT", "OFFSET", "UNION", "ALL", "DISTINCT", "AS", "CASE", "WHEN",
            "THEN", "ELSE", "END", "IF", "EXISTS"
        ]
        
        # Get the text content
        content = self.query_editor.get("1.0", tk.END)
        
        # Highlight keywords
        for keyword in keywords:
            start_pos = "1.0"
            while True:
                start_pos = self.query_editor.search(
                    r'\y' + keyword + r'\y', 
                    start_pos, 
                    tk.END, 
                    nocase=True, 
                    regexp=True
                )
                if not start_pos:
                    break
                end_pos = f"{start_pos}+{len(keyword)}c"
                self.query_editor.tag_add("keyword", start_pos, end_pos)
                start_pos = end_pos
    
    def execute_query(self):
        query = self.query_editor.get("1.0", tk.END).strip()
        if not query:
            messagebox.showwarning("Empty Query", "Please enter a SQL query to execute.")
            return
        
        # Update status
        self.status_var.set("Executing query...")
        self.root.update_idletasks()
        
        try:
            # Execute the query without using a cursor
            result = self.compiler.execute_without_cursor(query)
            
            # Add to history
            timestamp = datetime.now().strftime("%H:%M:%S")
            history_item = f"[{timestamp}] {query[:50]}{'...' if len(query) > 50 else ''}"
            self.history.append({"query": query, "timestamp": timestamp})
            self.history_list.insert(0, history_item)
            
            # Display results
            self.display_results(result)
            
            # Update status
            self.status_var.set(f"Query executed successfully at {timestamp}")
            
        except Exception as e:
            # Show error message
            self.display_error(str(e))
            self.status_var.set(f"Error: {str(e)}")
    
    def display_results(self, result):
        # Clear previous results
        for widget in self.table_frame.winfo_children():
            widget.destroy()
        
        # Switch to results tab
        self.results_notebook.select(0)
        
        # Check result type
        if isinstance(result, tuple) and len(result) == 2:
            # SELECT query result (columns, rows)
            columns, rows = result
            
            # Create treeview for results
            tree = ttk.Treeview(self.table_frame, columns=columns, show="headings")
            
            # Configure columns
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=100)
            
            # Add data
            for row in rows:
                tree.insert("", tk.END, values=row)
            
            # Add scrollbars
            x_scrollbar = ttk.Scrollbar(self.table_frame, orient=tk.HORIZONTAL, command=tree.xview)
            y_scrollbar = ttk.Scrollbar(self.table_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(xscrollcommand=x_scrollbar.set, yscrollcommand=y_scrollbar.set)
            
            # Pack everything
            tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Add row count label
            count_label = ttk.Label(
                self.table_frame, 
                text=f"Showing {len(rows)} rows",
                font=("Arial", 9),
                foreground="#666666"
            )
            count_label.pack(side=tk.BOTTOM, anchor=tk.W, padx=5, pady=2)
            
        elif isinstance(result, int):
            # Non-SELECT query (affected rows)
            message_label = ttk.Label(
                self.table_frame, 
                text=f"Query executed successfully. Affected rows: {result}",
                font=("Arial", 11)
            )
            message_label.pack(expand=True)
            
        else:
            # Other result type
            message_label = ttk.Label(
                self.table_frame, 
                text=f"Query executed successfully. Result: {result}",
                font=("Arial", 11)
            )
            message_label.pack(expand=True)
    
    def display_error(self, error_message):
        # Clear previous results
        for widget in self.table_frame.winfo_children():
            widget.destroy()
        
        # Switch to results tab
        self.results_notebook.select(0)
        
        # Create error frame
        error_frame = ttk.Frame(self.table_frame, padding=10)
        error_frame.pack(fill=tk.BOTH, expand=True)
        
        # Error title
        error_title = ttk.Label(
            error_frame, 
            text="Error",
            font=("Arial", 12, "bold"),
            foreground="#CC0000"
        )
        error_title.pack(anchor=tk.W, pady=(0, 5))
        
        # Error message
        error_text = scrolledtext.ScrolledText(
            error_frame,
            wrap=tk.WORD,
            width=40,
            height=10,
            font=("Consolas", 10),
            background="#FFEEEE",
            foreground="#CC0000"
        )
        error_text.pack(fill=tk.BOTH, expand=True)
        error_text.insert(tk.END, error_message)
        error_text.config(state=tk.DISABLED)
    
    def new_query(self):
        if messagebox.askyesno("New Query", "Clear the current query?"):
            self.query_editor.delete("1.0", tk.END)
            self.status_var.set("New query created")
    
    def open_query(self):
        file_path = filedialog.askopenfilename(
            defaultextension=".sql",
            filetypes=[("SQL files", "*.sql"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, "r") as file:
                    content = file.read()
                    self.query_editor.delete("1.0", tk.END)
                    self.query_editor.insert(tk.END, content)
                    self.status_var.set(f"Loaded query from {os.path.basename(file_path)}")
                    self.highlight_syntax()
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {str(e)}")
    
    def save_query(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".sql",
            filetypes=[("SQL files", "*.sql"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, "w") as file:
                    content = self.query_editor.get("1.0", tk.END)
                    file.write(content)
                    self.status_var.set(f"Saved query to {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {str(e)}")
    
    def clear_editor(self):
        if messagebox.askyesno("Clear Editor", "Clear the current query?"):
            self.query_editor.delete("1.0", tk.END)
            self.status_var.set("Editor cleared")
    
    def load_from_history(self, event):
        selected_index = self.history_list.curselection()
        if selected_index:
            # Get the selected history item
            index = selected_index[0]
            if index < len(self.history):
                # Load the query into the editor
                self.query_editor.delete("1.0", tk.END)
                self.query_editor.insert(tk.END, self.history[index]["query"])
                self.highlight_syntax()
                self.status_var.set(f"Loaded query from history ({self.history[index]['timestamp']})")
    
    def show_about(self):
        messagebox.showinfo(
            "About SQL Compiler",
            "SQL Compiler\nVersion 1.0\nDeveloped by [Your Name]"
        )

# Main
if __name__ == "__main__":
    root = tk.Tk()
    app = SQLCompilerUI(root)
    root.mainloop()
