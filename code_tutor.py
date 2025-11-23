import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import io
import contextlib
import traceback
import os
from datetime import datetime
import sys  # used for tracing

# --- IDLE-style syntax highlighting ---
from idlelib.colorizer import ColorDelegator
from idlelib.percolator import Percolator


class MiniNotebookApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Code Tutor")

        # This dict will store variables/functions between runs (like a notebook)
        self.execution_env = {}

        self._build_ui()
        self._create_menu()
        self._bind_shortcuts()

        # Handle window close (no save prompt)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------------- UI BUILDING ----------------

    def _build_ui(self):
        self.root.geometry("500x500")

        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Code label
        code_label = ttk.Label(main_frame, text="Python code:")
        code_label.pack(anchor="w")

        # Code text area + scrollbar
        code_frame = ttk.Frame(main_frame)
        code_frame.pack(fill=tk.BOTH, expand=True)

        # Main code Text widget
        self.code_text = tk.Text(
            code_frame,
            height=15,
            wrap="none",
            font=("Consolas", 11),
            undo=True,
        )
        self.code_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Vertical scrollbar for code
        self.code_scroll = ttk.Scrollbar(
            code_frame, orient="vertical", command=self.code_text.yview
        )
        self.code_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.code_text.configure(yscrollcommand=self.code_scroll.set)

        # Attach IDLE syntax highlighter
        Percolator(self.code_text).insertfilter(ColorDelegator())

        # Track cursor movement for status bar
        self.code_text.bind("<KeyRelease>", self.update_status)
        self.code_text.bind("<ButtonRelease-1>", self.update_status)

        # Tab inserts 4 spaces
        self.code_text.bind("<Tab>", self.insert_tab_spaces)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(8, 4))

        run_button = ttk.Button(btn_frame, text="Run (Ctrl+Enter)", command=self.run_code)
        run_button.pack(side=tk.LEFT)

        clear_out_button = ttk.Button(btn_frame, text="Clear Output", command=self.clear_output)
        clear_out_button.pack(side=tk.LEFT, padx=(8, 0))

        clear_code_button = ttk.Button(btn_frame, text="Clear Code", command=self.clear_code)
        clear_code_button.pack(side=tk.LEFT, padx=(8, 0))

        reset_env_button = ttk.Button(btn_frame, text="Reset Env", command=self.reset_environment)
        reset_env_button.pack(side=tk.LEFT, padx=(8, 0))

        # Explain Step-by-Step button (now always Kid-style)
        explain_button = ttk.Button(
            btn_frame,
            text="Explain Step-by-Step",
            command=self.explain_step_by_step
        )
        explain_button.pack(side=tk.LEFT, padx=(8, 0))

        # Output label
        out_label = ttk.Label(main_frame, text="Output:")
        out_label.pack(anchor="w", pady=(8, 0))

        # Output text area + scrollbar
        out_frame = ttk.Frame(main_frame)
        out_frame.pack(fill=tk.BOTH, expand=True)

        self.output_text = tk.Text(
            out_frame,
            height=10,
            wrap="none",
            font=("Consolas", 11),
            state="normal",
            bg="white",
            fg="black",
            insertbackground="black",
        )
        self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        out_scroll = ttk.Scrollbar(
            out_frame, orient="vertical", command=self.output_text.yview
        )
        out_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.output_text.configure(yscrollcommand=out_scroll.set)

        # Status bar (line/column, last run)
        self.status_var = tk.StringVar()
        self.status_var.set("Ln 1, Col 1")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, anchor="w")
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))

        # Starter example in the code box
        starter = (
            "count = 0\n"
            "for i in range(1, 5):\n"
            "    count += i\n"
            "print(count)\n"
        )
        self.code_text.insert("1.0", starter)
        self.code_text.edit_reset()  # reset undo/redo stack

    def _create_menu(self):
        menubar = tk.Menu(self.root)

        # File menu – only Exit now
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Exit", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        # Run menu
        run_menu = tk.Menu(menubar, tearoff=False)
        run_menu.add_command(label="Run", command=self.run_code, accelerator="Ctrl+Enter")
        run_menu.add_command(
            label="Run Selection", command=self.run_selection, accelerator="Shift+Enter"
        )
        run_menu.add_command(label="Reset Environment", command=self.reset_environment)
        menubar.add_cascade(label="Run", menu=run_menu)

        # Examples menu
        examples_menu = tk.Menu(menubar, tearoff=False)
        examples_menu.add_command(
            label="Loop: Sum 1 to 4",
            command=lambda: self.load_example("loop_sum"),
        )
        examples_menu.add_command(
            label="Strings: basic operations",
            command=lambda: self.load_example("string_ops"),
        )
        examples_menu.add_command(
            label="Lists: average of numbers",
            command=lambda: self.load_example("list_average"),
        )
        examples_menu.add_command(
            label="Functions: greeting",
            command=lambda: self.load_example("function_greet"),
        )
        examples_menu.add_command(
            label="If/elif: grade checker",
            command=lambda: self.load_example("grade_checker"),
        )
        examples_menu.add_separator()
        examples_menu.add_command(
            label="Dictionaries: word meanings",
            command=lambda: self.load_example("dict_lookup"),
        )
        examples_menu.add_command(
            label="While loop: countdown",
            command=lambda: self.load_example("while_countdown"),
        )
        examples_menu.add_command(
            label="List comprehension: squares",
            command=lambda: self.load_example("list_comprehension"),
        )
        examples_menu.add_command(
            label="Tuples: unpacking coordinates",
            command=lambda: self.load_example("tuple_unpack"),
        )
        examples_menu.add_command(
            label="Try/except: safe division",
            command=lambda: self.load_example("try_except"),
        )
        menubar.add_cascade(label="Examples", menu=examples_menu)

        self.root.config(menu=menubar)

    def _bind_shortcuts(self):
        # Only run-related shortcuts
        self.root.bind("<Control-Return>", lambda e: self.run_code())
        self.root.bind("<Shift-Return>", self._run_selection_event)

    # ---------------- EDITOR BEHAVIOUR ----------------

    def insert_tab_spaces(self, event):
        """Insert 4 spaces when Tab is pressed."""
        self.code_text.insert("insert", " " * 4)
        return "break"   # Stop the default behaviour

    def update_status(self, event=None, extra_info=""):
        """Update the status bar with current line/column and optional extra info."""
        try:
            index = self.code_text.index("insert")
            line, col = index.split(".")
            # Column is zero-based internally; show as 1-based
            text = f"Ln {int(line)}, Col {int(col) + 1}"
            if extra_info:
                text += " | " + extra_info
            self.status_var.set(text)
        except tk.TclError:
            pass  # happens if widget not yet fully initialised

    # ---------------- RUNNING CODE ----------------

    def run_code(self):
        """Run the entire code cell."""
        code = self.code_text.get("1.0", tk.END)

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            try:
                exec(code, self.execution_env)
            except Exception:
                traceback.print_exc()

        output = buffer.getvalue()
        if not output.strip():
            output = "[No output]\n"

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.output_text.insert(tk.END, f"--- Run at {timestamp} ---\n")
        self.output_text.insert(tk.END, output + "\n")
        self.output_text.see(tk.END)

        self.update_status(extra_info=f"Last run: {timestamp}")

    def _run_selection_event(self, event):
        self.run_selection()
        return "break"

    def run_selection(self):
        """Run only the selected code, or the current line if nothing is selected."""
        try:
            code = self.code_text.get("sel.first", "sel.last")
        except tk.TclError:
            # No selection: run the current line
            index = self.code_text.index("insert linestart")
            end_index = self.code_text.index("insert lineend")
            code = self.code_text.get(index, end_index) + "\n"

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            try:
                exec(code, self.execution_env)
            except Exception:
                traceback.print_exc()

        output = buffer.getvalue()
        if not output.strip():
            output = "[No output]\n"

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.output_text.insert(tk.END, f"--- Run selection at {timestamp} ---\n")
        self.output_text.insert(tk.END, output + "\n")
        self.output_text.see(tk.END)

        self.update_status(extra_info=f"Last run: {timestamp}")

    def reset_environment(self):
        """Clear the execution environment (variables, functions, etc.)."""
        self.execution_env.clear()
        # Ensure builtins remain available
        self.execution_env["__builtins__"] = __builtins__
        self.update_status(extra_info="Environment reset")

    # ---------------- STEP-BY-STEP EXPLANATION (always Kid-style) ----------------

    def explain_step_by_step(self):
        """Trace the code line-by-line and show kid-style explanation."""
        code = self.code_text.get("1.0", tk.END)
        if not code.strip():
            messagebox.showinfo("No code", "There is no code to explain.")
            return

        code_lines = code.splitlines()
        max_steps = 200  # safety: avoid infinite loops in explanations
        buffer = io.StringIO()

        # We'll store structured steps: lineno, line text, and locals (repr strings)
        steps = []

        def trace_fn(frame, event, arg):
            nonlocal steps
            # Only trace lines in this code snippet (filename <string>)
            if event == "line" and frame.f_code.co_filename == "<string>":
                lineno = frame.f_lineno
                if 1 <= lineno <= len(code_lines):
                    line_text = code_lines[lineno - 1].rstrip("\n")
                else:
                    line_text = ""

                # Build a snapshot of locals (repr string for each)
                locals_snapshot = {}
                for name, value in frame.f_locals.items():
                    if name.startswith("__") and name.endswith("__"):
                        continue
                    try:
                        rep = repr(value)
                    except Exception:
                        rep = f"<unreprable {type(value).__name__}>"
                    if len(rep) > 60:
                        rep = rep[:57] + "..."
                    locals_snapshot[name] = rep

                steps.append(
                    {
                        "lineno": lineno,
                        "line": line_text,
                        "locals": locals_snapshot,
                    }
                )

                if len(steps) >= max_steps:
                    return None

            return trace_fn

        # Use a fresh environment just for explanation
        env = {"__builtins__": __builtins__}
        try:
            compiled = compile(code, "<string>", "exec")
        except SyntaxError as e:
            self.output_text.insert(
                tk.END,
                f"--- Step-by-step (syntax error) ---\n{e}\n\n"
            )
            self.output_text.see(tk.END)
            return

        old_trace = sys.gettrace()
        timestamp = datetime.now().strftime("%H:%M:%S")

        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            try:
                sys.settrace(trace_fn)
                exec(compiled, env)
            except Exception:
                traceback.print_exc()
            finally:
                sys.settrace(old_trace)

        printed_output = buffer.getvalue()

        # Always use kid-style formatter
        rendered_lines = self._format_kid_style(steps, env)

        # Write everything into the output box
        self.output_text.insert(tk.END, f"--- Step-by-step at {timestamp} ---\n")
        if rendered_lines:
            for line in rendered_lines:
                self.output_text.insert(tk.END, line + "\n")
        else:
            self.output_text.insert(
                tk.END,
                "[No steps traced – the code may be empty or didn't execute any lines]\n"
            )

        if len(steps) >= max_steps:
            self.output_text.insert(
                tk.END,
                f"\n[Stopped after {max_steps} steps to avoid a very long trace]\n"
            )

        if printed_output.strip():
            self.output_text.insert(
                tk.END,
                "\n--- Printed output during explanation ---\n"
            )
            self.output_text.insert(tk.END, printed_output + "\n\n")
        else:
            self.output_text.insert(tk.END, "\n")

        self.output_text.see(tk.END)
        self.update_status(extra_info=f"Step-by-step at {timestamp}")

    def _format_normal_style(self, steps):
        """(Unused now) Simpler 'adult' mode: line numbers + locals, skipping repeated loop headers."""
        lines = []
        seen_loop_lines = set()

        for s in steps:
            lineno = s["lineno"]
            line_text = s["line"]
            locals_dict = s["locals"]
            stripped = line_text.lstrip()

            # For 'for' and 'while' lines, only show first time
            if stripped.startswith(("for ", "while ")):
                if lineno in seen_loop_lines:
                    continue
                seen_loop_lines.add(lineno)

            if locals_dict:
                locals_str = ", ".join(f"{k}={v}" for k, v in locals_dict.items())
                lines.append(f"Line {lineno}: {line_text}\n    Locals: {locals_str}")
            else:
                lines.append(f"Line {lineno}: {line_text}")

        return lines


    def _format_kid_style(self, steps, env):
        """
        Kid-style mode:
        - Talks in 'Step 1, Step 2...' language
        - Only highlights variables that actually change (or appear/disappear)
        - Uses the *next* step's locals as the 'after' state
        - Numbers steps sequentially (no gaps)
        - Skips noisy things like function objects (e.g. greet at 0x...)
        """
        lines = []
        if not steps:
            return lines

        # Snapshot of final environment, in case we need it for the last step
        final_env_snapshot = {}
        for name, value in env.items():
            if name.startswith("__") and name.endswith("__"):
                continue
            try:
                rep = repr(value)
            except Exception:
                rep = f"<unreprable {type(value).__name__}>"
            if len(rep) > 60:
                rep = rep[:57] + "..."
            final_env_snapshot[name] = rep

        seen_loop_lines = set()

        lines.append("We are going to walk through your code one step at a time.")

        step_counter = 0  # we control the visible step numbers

        for idx, s in enumerate(steps):
            lineno = s["lineno"]
            line_text = s["line"]
            before_locals = s["locals"]
            stripped = line_text.lstrip()

            # Decide 'after' locals: next step's locals, or final env if this is last
            if idx + 1 < len(steps):
                after_locals = steps[idx + 1]["locals"]
            else:
                after_locals = final_env_snapshot

            # Describe the line (with nice step numbers)
            if stripped.startswith("for "):
                if lineno in seen_loop_lines:
                    # don't re-explain the same for-loop header
                    continue
                seen_loop_lines.add(lineno)
                step_counter += 1
                lines.append(
                    f"\nStep {step_counter}: We set up a loop:\n"
                    f"    {line_text}\n"
                    "This means we will repeat the indented lines for each value."
                )
            elif stripped.startswith("while "):
                if lineno in seen_loop_lines:
                    continue
                seen_loop_lines.add(lineno)
                step_counter += 1
                lines.append(
                    f"\nStep {step_counter}: We set up a while-loop:\n"
                    f"    {line_text}\n"
                    "This means we will keep repeating while the condition is True."
                )
            else:
                step_counter += 1
                lines.append(f"\nStep {step_counter}: We run this line:\n    {line_text}")

            # Build explanation of variables before/after
            changed_bits = []
            unchanged_bits = []

            all_names = set(before_locals.keys()) | set(after_locals.keys())
            for name in sorted(all_names):
                before_val = before_locals.get(name)
                after_val = after_locals.get(name)

                # Skip noisy function objects like "<function greet at 0x...>"
                if (before_val and before_val.startswith("<function")) or (
                    after_val and after_val.startswith("<function")
                ):
                    continue

                if before_val != after_val:
                    # Something changed (or appeared/disappeared)
                    if before_val is None and after_val is not None:
                        changed_bits.append(f"{name} is now {after_val}")
                    elif before_val is not None and after_val is None:
                        changed_bits.append(f"{name} used to be {before_val} here")
                    else:
                        changed_bits.append(
                            f"{name} goes from {before_val} to {after_val}"
                        )
                else:
                    # Same value before and after – only used as fallback
                    unchanged_bits.append(f"{name} is {after_val}")

            # Keep it short: focus on changes, only a tiny bit of context
            max_items = 3

            if changed_bits:
                changed_bits = changed_bits[:max_items]
                lines.append("  After this step:")
                for text in changed_bits:
                    lines.append(f"    • {text}")
            else:
                # If nothing (interesting) changed, show up to 2 unchanged vars for context
                if unchanged_bits:
                    for text in unchanged_bits[:2]:
                        lines.append(f"  Here we have: {text}")

        return lines

    # ---------------- EXAMPLES ----------------

    def load_example(self, key: str):
        """Load one of the predefined educational examples into the editor."""
        examples = {
            "loop_sum": (
                "count = 0\n"
                "for i in range(1, 5):\n"
                "    count += i\n"
                "print(\"Final count is\", count)\n"
            ),
            "string_ops": (
                "text = \"Hello, world!\"\n"
                "print(text)\n"
                "print(text.upper())\n"
                "print(text.lower())\n"
                "print(text.replace(\"world\", \"Python\"))\n"
                "print(\"Length of text:\", len(text))\n"
            ),
            "list_average": (
                "numbers = [10, 20, 30, 40]\n"
                "total = 0\n"
                "for n in numbers:\n"
                "    total += n\n"
                "\n"
                "average = total / len(numbers)\n"
                "print(\"Numbers:\", numbers)\n"
                "print(\"Total:\", total)\n"
                "print(\"Average:\", average)\n"
            ),
            "function_greet": (
                "def greet(name):\n"
                "    message = f\"Hello, {name}!\"\n"
                "    print(message)\n"
                "    return message\n"
                "\n"
                "greet(\"Alice\")\n"
                "greet(\"Bob\")\n"
            ),
            "grade_checker": (
                "score = 73\n"
                "\n"
                "if score >= 80:\n"
                "    grade = \"A\"\n"
                "elif score >= 70:\n"
                "    grade = \"B\"\n"
                "elif score >= 60:\n"
                "    grade = \"C\"\n"
                "else:\n"
                "    grade = \"D\"\n"
                "\n"
                "print(\"Score:\", score)\n"
                "print(\"Grade:\", grade)\n"
            ),
            "dict_lookup": (
                "words = {\n"
                "    \"python\": \"a programming language\",\n"
                "    \"loop\": \"a way to repeat code\",\n"
                "    \"variable\": \"a named place to store a value\",\n"
                "}\n"
                "\n"
                "key = \"loop\"\n"
                "meaning = words.get(key, \"(not found)\")\n"
                "print(f\"Word: {key}\")\n"
                "print(f\"Meaning: {meaning}\")\n"
            ),
            "while_countdown": (
                "n = 5\n"
                "while n > 0:\n"
                "    print(\"Counting down:\", n)\n"
                "    n -= 1\n"
                "print(\"Lift off!\")\n"
            ),
            "list_comprehension": (
                "numbers = [1, 2, 3, 4, 5]\n"
                "squares = [n * n for n in numbers]\n"
                "print(\"Numbers:\", numbers)\n"
                "print(\"Squares:\", squares)\n"
            ),
            "tuple_unpack": (
                "point = (4, 7)\n"
                "x, y = point\n"
                "print(\"Point:\", point)\n"
                "print(\"x coordinate:\", x)\n"
                "print(\"y coordinate:\", y)\n"
            ),
            "try_except": (
                "text = \"12\"  # try changing this to \"abc\" and run again\n"
                "\n"
                "try:\n"
                "    number = int(text)\n"
                "    result = 100 / number\n"
                "    print(\"Text as int:\", number)\n"
                "    print(\"100 divided by\", number, \"is\", result)\n"
                "except ValueError:\n"
                "    print(\"Cannot convert text to an integer.\")\n"
                "except ZeroDivisionError:\n"
                "    print(\"Cannot divide by zero.\")\n"
            ),
        }

        code = examples.get(key)
        if code is None:
            return

        # Replace editor contents with the chosen example
        self.code_text.delete("1.0", tk.END)
        self.code_text.insert("1.0", code)
        self.code_text.edit_reset()
        self.update_status()

    # ---------------- CLEARING ----------------

    def clear_output(self):
        self.output_text.delete("1.0", tk.END)

    def clear_code(self):
        self.code_text.delete("1.0", tk.END)
        self.update_status()

    # ---------------- WINDOW CLOSE ----------------

    def on_close(self):
        self.root.destroy()


def main():
    root = tk.Tk()
    app = MiniNotebookApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
