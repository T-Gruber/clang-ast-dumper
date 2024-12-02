import clang.cindex
import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox


class ClangASTDumper:
    def __init__(self):
        self.filename = ""
        self.index = None
        self.translation_unit = None
        self.global_nodes = []
        self.source_code = []
        self.tu_cursor_name = "translation_unit"

        self.root = tk.Tk()
        self.root.configure(background="black")
        self.root.title("Clang AST Dumper")
        self.default_height = 600
        self.default_width = 800
        self.root.geometry(f"{self.default_width}x{self.default_height}")
        self.search_var = tk.StringVar()
        self.file_var = tk.StringVar()
        self.setup_ui()
        self.root.mainloop()

    def load_file(self) -> None:
        """Load the source code and parse the AST of the given file."""
        self.filename = self.file_var.get().strip()
        if not os.path.exists(self.filename) or not os.path.isfile(
            self.filename
        ):
            messagebox.showerror("Error", f"File '{self.filename}' not found.")
            return

        self.index = clang.cindex.Index.create()
        try:
            self.translation_unit = self.index.parse(self.filename)
        except clang.cindex.TranslationUnitLoadError as e:
            messagebox.showerror("Error", f"Failed to parse the AST:\n{e}")
            return
        self.global_nodes = self.get_global_nodes()
        self.source_code = self.get_source_code()
        messagebox.showinfo("Success", "Loaded source code and AST")

    def get_source_code(self) -> list:
        """Extracts the source code of the translation unit.

        ### Output:
            - (`list`). Source code lines of the current input file.
        """
        try:
            with open(self.filename, "r") as f:
                source_lines = f.readlines()
                return source_lines
        except FileNotFoundError:
            messagebox.showerror("Error", f"File '{self.filename}' not found.")
            return []
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file:\n{e}")
            return []

    def get_global_nodes(self) -> dict:
        """Extracts global nodes from the translation unit.

        ### Output:
            - (`dict`). Definition and/or declaration cursor for
            each global symbol found.
        """
        global_nodes = {}
        for cursor in self.translation_unit.cursor.get_children():
            cursor_name = cursor.spelling
            if cursor_name not in global_nodes.keys():
                global_nodes[cursor_name] = {}
            if cursor.is_definition():
                global_nodes[cursor_name]["def"] = cursor
            else:
                global_nodes[cursor_name]["decl"] = cursor
        return global_nodes

    def setup_ui(self) -> None:
        """Initializes the UI layout."""
        # File select Section
        file_frame = tk.Frame(self.root)
        file_frame.pack(fill=tk.X)
        tk.Label(file_frame, text="Input file:").pack(side=tk.LEFT)
        file_entry = tk.Entry(file_frame, textvariable=self.file_var)
        file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        file_entry.configure(background="grey80")
        file_button = tk.Button(
            file_frame, text="Load", command=self.load_file
        )
        file_button.pack(side=tk.LEFT)

        # Symbol search Section
        search_frame = tk.Frame(self.root)
        search_frame.pack(fill=tk.X)
        tk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        search_entry = tk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.configure(background="grey80")
        # start_search = lambda event=None: self.search_symbol()
        search_entry.bind("<Return>", lambda event=None: self.search_symbol())
        search_button = tk.Button(
            search_frame, text="Search", command=self.search_symbol
        )
        search_button.pack(side=tk.LEFT)

        # Split window for code and AST
        p_window = tk.PanedWindow(self.root)
        p_window.pack(fill=tk.BOTH, expand=1)

        # Code section
        self.code_text = scrolledtext.ScrolledText(p_window, wrap=tk.WORD)
        self.code_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(self.code_text, text="Source Code").pack(side=tk.TOP)
        p_window.add(self.code_text)

        # AST section
        self.ast_tree = ttk.Treeview(p_window)
        self.ast_tree.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        tk.Label(self.ast_tree, text="Clang AST").pack(side=tk.TOP)
        p_window.add(self.ast_tree)

        p_window.paneconfig(self.code_text, width=int(self.default_width / 2))
        p_window.paneconfig(self.ast_tree, width=int(self.default_width / 2))

        self.root.mainloop()

    def search_symbol(self) -> None:
        """Searches for a symbol and updates the AST and source code
        display.
        """
        symbol_name = self.search_var.get().strip()
        # Update with given symbol node
        if symbol_name in self.global_nodes:
            self.update_ast_view(symbol_name)
            self.update_code_view(symbol_name)
        # Update with translationunit node as default node
        elif symbol_name == "":
            self.update_ast_view(self.tu_cursor_name)
            self.update_code_view(self.tu_cursor_name)
        # Given node not found
        else:
            self.code_text.delete(1.0, tk.END)
            self.code_text.insert(
                tk.END, f"No symbol found for '{symbol_name}'"
            )
            self.ast_tree.delete()
            self.update_ast_view(self.tu_cursor_name)

    def update_ast_view(self, cursor_name: str) -> None:
        """Displays the AST for the given cursor.

        ### Input:
            - cursor_name (`str`). Name of the cursor to a global symbol.
        """
        self.ast_tree.delete(
            *self.ast_tree.get_children()
        )  # Clear previous tree
        if cursor_name == self.tu_cursor_name:
            self.populate_ast_tree(self.translation_unit.cursor, "")
        else:
            cursor_info = self.global_nodes[cursor_name]
            if "decl" in cursor_info.keys():
                self.populate_ast_tree(cursor_info["decl"], "")
            if "def" in cursor_info.keys():
                self.populate_ast_tree(cursor_info["def"], "")

    def populate_ast_tree(
        self, cursor: clang.cindex.Cursor, parent_id: str
    ) -> None:
        """Populates the AST tree of a given cursor.

        ### Input:
            - cursor (`clang.cindex.Cursor`). Parent cursor used as
            root of the AST tree.
            - parent_id (`str`). ID of the parent cursor.
        """
        stack = [(cursor, parent_id)]
        while stack:
            current_cursor, current_parent = stack.pop()
            cursor_name = current_cursor.displayname
            node_id = self.ast_tree.insert(
                current_parent,
                "end",
                text=f"{current_cursor.kind}{': ' if cursor_name else ''}"
                f"{cursor_name}",
            )
            self.ast_tree.item(node_id, open=True)
            for child in current_cursor.get_children():
                stack.append((child, node_id))

    def get_cursor_code(self, cursor: clang.cindex.Cursor) -> str:
        """Get the source code for a cursor in the AST.

        ### Input:
            - cursor (`clang.cindex.Cursor`). Given cursor.

        ### Output:
            - (`str`). Source code of the given cursor.
        """
        extent = cursor.extent
        start_line, start_col = extent.start.line - 1, extent.start.column - 1
        end_line, end_col = extent.end.line - 1, extent.end.column - 1

        selected_code = "".join(self.source_code[start_line : end_line + 1])
        if end_line == start_line:
            selected_code = selected_code[start_col:end_col]
        return selected_code

    def update_code_view(self, cursor_name: str) -> None:
        """Displays the source code of the selected symbol.

        ### Input:
            - cursor_name (`str`). Name of the cursor to a global symbol.
        """

        # Set text modifiable
        self.code_text.config(state=tk.NORMAL)

        selected_code = ""
        if cursor_name == self.tu_cursor_name:
            selected_code = "\n\n" + self.get_cursor_code(
                self.translation_unit.cursor
            )

        else:
            cursor_info = self.global_nodes[cursor_name]
            if "decl" in cursor_info.keys():
                decl_cursor = cursor_info["decl"]
                selected_code += (
                    "\n\n// Declaration\n\n"
                    + self.get_cursor_code(decl_cursor)
                )
            if "def" in cursor_info.keys():
                decl_cursor = cursor_info["def"]
                selected_code += (
                    "\n\n// Definition\n\n" + self.get_cursor_code(decl_cursor)
                )

        self.code_text.delete(1.0, tk.END)
        self.code_text.insert(tk.END, selected_code)
        # Set text to read-only
        self.code_text.config(state=tk.DISABLED)


if __name__ == "__main__":
    ClangASTDumper()
