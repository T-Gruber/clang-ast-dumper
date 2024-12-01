import clang.cindex
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext


class ClangASTDumper:
    def __init__(self, filename: str):
        self.filename = filename
        self.index = clang.cindex.Index.create()
        self.translation_unit = self.index.parse(filename)
        self.global_nodes = self.get_global_nodes()
        self.source_code = self.get_source_code()
        self.tu_cursor_name = "translation_unit"

        self.root = tk.Tk()
        self.root.configure(background="black")
        self.root.title("Clang AST Dumper")
        self.default_height = 600
        self.default_width = 800
        self.root.geometry(f"{self.default_width}x{self.default_height}")
        self.search_var = tk.StringVar()
        self.setup_ui()
        self.root.mainloop()

    def get_source_code(self) -> list:
        """Extracts the source code of the translation unit."""
        source_lines = []
        with open(self.filename, "r") as f:
            source_lines = f.readlines()
        return source_lines

    def get_global_nodes(self) -> dict:
        """Extracts global nodes from the translation unit."""
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
        # Search Section
        search_frame = tk.Frame(self.root)
        search_frame.pack(fill=tk.X)
        tk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        search_entry = tk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.configure(background="grey80")
        start_search = lambda event=None: self.search_symbol()
        search_entry.bind("<Return>", start_search)
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
        """Searches for a symbol and updates the AST and source code display."""
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
            self.code_text.insert(tk.END, f"No symbol found for '{symbol_name}'")
            self.ast_tree.delete()
            self.update_ast_view(self.tu_cursor_name)

    def update_ast_view(self, cursor_name: str) -> None:
        """Displays the AST for the given cursor."""
        self.ast_tree.delete(*self.ast_tree.get_children())  # Clear previous tree
        if cursor_name == self.tu_cursor_name:
            self.populate_ast_tree(self.translation_unit.cursor, "")
        else:
            cursor_info = self.global_nodes[cursor_name]
            if "decl" in cursor_info.keys():
                self.populate_ast_tree(cursor_info["decl"], "")
            if "def" in cursor_info.keys():
                self.populate_ast_tree(cursor_info["def"], "")

    def populate_ast_tree(self, cursor: clang.cindex.Cursor, parent_id: str) -> None:
        """Recursively populates the AST tree."""
        cursor_name = cursor.displayname
        node_id = self.ast_tree.insert(
            parent_id,
            "end",
            text=f"{cursor.kind}{': ' if cursor_name else ''}{cursor_name}",
        )

        self.ast_tree.item(node_id, open=True)
        for child in cursor.get_children():
            self.populate_ast_tree(child, node_id)

    def get_cursor_code(self, cursor: clang.cindex.Cursor) -> str:
        extent = cursor.extent
        start_line, start_col = extent.start.line - 1, extent.start.column - 1
        end_line, end_col = extent.end.line - 1, extent.end.column - 1

        selected_code = "".join(self.source_code[start_line : end_line + 1])
        if end_line == start_line:
            selected_code = selected_code[start_col:end_col]
        return selected_code

    def update_code_view(self, cursor_name: str) -> None:
        """Displays the source code of the selected symbol."""

        # Set text modifiable
        self.code_text.config(state=tk.NORMAL)

        selected_code = ""
        if cursor_name == self.tu_cursor_name:
            selected_code = "\n\n" + self.get_cursor_code(self.translation_unit.cursor)

        else:
            cursor_info = self.global_nodes[cursor_name]
            if "decl" in cursor_info.keys():
                decl_cursor = cursor_info["decl"]
                selected_code += "\n\n// Declaration\n\n" + self.get_cursor_code(
                    decl_cursor
                )
            if "def" in cursor_info.keys():
                decl_cursor = cursor_info["def"]
                selected_code += "\n\n// Definition\n\n" + self.get_cursor_code(
                    decl_cursor
                )

        self.code_text.delete(1.0, tk.END)
        self.code_text.insert(tk.END, selected_code)
        # Set text to read-only
        self.code_text.config(state=tk.DISABLED)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python clang_ast_dumper.py <C-file>")
        sys.exit(1)

    source_filename = sys.argv[1]
    ClangASTDumper(source_filename)
