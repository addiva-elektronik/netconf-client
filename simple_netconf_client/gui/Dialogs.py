import markdown
import customtkinter as ctk
from tkinterweb import HtmlFrame
from tkinter import  END, Listbox
from simple_netconf_client import get_version


class AboutDialog(ctk.CTkToplevel):
    def __init__(self, parent, width, height):
        super().__init__(parent)
        self.title("About")
        parent.center_dialog(self, width, height)
        about_message = (
            "Simple NETCONF Client\n"
            f"v{get_version()}\n"
            "\n"
            "Copyright (c) 2024 Ejub Šabić et al.\n"
            "\n"
            "This program is available for free as\n"
            "open source under the MIT license.\n"
        )
        label = ctk.CTkLabel(self, text=about_message, font=("Arial", 14))
        label.pack(padx=20, pady=20)
        close_button = ctk.CTkButton(self, text="Close", command=self.destroy)
        close_button.pack(pady=10)

        # Allow closing with common key bindings
        self.bind("<Control-w>", lambda event: self.destroy())
        self.bind("<Escape>", lambda event: self.destroy())
        # Bring frame into foreground and focus it when it becomes visible
        self.bind("<Map>", self.on_map)

    def on_map(self, event):
        self.lift()
        self.focus_force()

class LicenseDialog(ctk.CTkToplevel):
    def __init__(self, parent, width, height):
        super().__init__(parent)
        self.title("License")
        parent.center_dialog(self, width, height)
        license_message = (
            "MIT License\n\n"
            "Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the 'Software'), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:\n\n"
            "The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.\n\n"
            "THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE."
        )
        label = ctk.CTkLabel(self, text=license_message,
                             font=("Arial", 14),
                             wraplength=580)
        label.pack(padx=20, pady=20)
        close_button = ctk.CTkButton(self, text="Close", command=self.destroy)
        close_button.pack(pady=10)

        # Allow closing with common key bindings
        self.bind("<Control-w>", lambda event: self.destroy())
        self.bind("<Escape>", lambda event: self.destroy())
        # Bring frame into foreground and focus it when it becomes visible
        self.bind("<Map>", self.on_map)

    def on_map(self, event):
        self.lift()
        self.focus_force()


class UsageDialog(ctk.CTkToplevel):
    def __init__(self, parent, content, width=800, height=600):
        super().__init__(parent)
        self.parent = parent

        self.title("Usage")
        parent.center_dialog(self, width, height)

        # Initialize history tracking
        self.history = []
        self.history_index = -1

        # Apply dark mode CSS if needed
        css = """
        body { font-family: Arial, sans-serif; }
        pre { background-color: #2e2e2e; color: #f8f8f2; padding: 10px; }
        code { background-color: #2e2e2e; color: #f8f8f2; }
        body { background-color: #1e1e1e; color: #f8f8f2; }
        a { color: #1e90ff; text-decoration: underline; }
        blockquote { border-left: 4px solid #1e90ff; padding-left: 10px; margin-left: 0; color: #888; }
        """ if ctk.get_appearance_mode() == "Dark" else """
        body { font-family: Arial, sans-serif; }
        pre { background-color: #f8f8f2; color: #2e2e2e; padding: 10px; }
        code { background-color: #f8f8f2; color: #2e2e2e; }
        body { background-color: #ffffff; color: #000000; }
        a { color: #0000ff; text-decoration: underline; }
        blockquote { border-left: 4px solid #0000ff; padding-left: 10px; margin-left: 0; color: #555; }
        """

        self.html_content = f"""
        <html>
        <head>
            <style>{css}</style>
        </head>
        <body>
            {markdown.markdown(content, extensions=['fenced_code', 'codehilite', 'extra'])}
        </body>
        </html>
        """

        self.html_frame = HtmlFrame(self, horizontal_scrollbar="auto", messages_enabled=False)
        self.html_frame.load_html(self.html_content)
        self.html_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Back and Forward buttons
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(fill="x", padx=10, pady=5)

        self.back_button = ctk.CTkButton(self.button_frame, text="Back", command=self.go_back)
        self.back_button.pack(side="left", padx=5)
        self.back_button.configure(state="disabled")

        self.forward_button = ctk.CTkButton(self.button_frame, text="Forward", command=self.go_forward)
        self.forward_button.pack(side="left", padx=5)
        self.forward_button.configure(state="disabled")

        self.close_button = ctk.CTkButton(self.button_frame, text="Close", command=self.destroy)
        self.close_button.pack(side="right", pady=10)

        # Add initial content to history
        self.add_to_history(self.html_content, is_url=False)

        # Hook into link loader
        self.html_frame.on_link_click(self.load_html_content)

        # Bind mouse back/forward buttons
        #self.bind("<Button-8>", self.on_back_button)
        #self.bind("<Button-9>", self.on_forward_button)

        self.html_frame.bind_all("<Alt-Left>", self.on_back_button)
        self.html_frame.bind_all("<Alt-Right>", self.on_forward_button)

        # Bind key events for scrolling and closing
        self.html_frame.bind_all("<Up>", lambda e: self.html_frame.yview_scroll(-5, "units"))
        self.html_frame.bind_all("<Down>", lambda e: self.html_frame.yview_scroll(5, "units"))
        self.html_frame.bind_all("<Prior>", lambda e: self.html_frame.yview_scroll(-1, "pages"))
        self.html_frame.bind_all("<Next>", lambda e: self.html_frame.yview_scroll(1, "pages"))
        self.html_frame.bind_all("<Home>", lambda e: self.html_frame.yview_moveto(0))
        self.html_frame.bind_all("<End>", lambda e: self.html_frame.yview_moveto(1))
        self.bind("<Control-w>", lambda event: self.destroy())
        self.bind("<Escape>", lambda event: self.destroy())

        # Bind right-click on links to copy URL
        self.html_frame.bind("<Button-3>", self.on_right_click)

        # Bring frame into foreground and focus it when it becomes visible
        self.html_frame.bind("<Map>", self.on_map)

    def on_map(self, event):
        self.lift()
        self.focus_force()

    def dummy(self, event):
        return

    def add_to_history(self, content, is_url):
        if self.history_index == -1 or (self.history and self.history[self.history_index] != content):
            self.history = self.history[:self.history_index + 1]
            self.history.append((content, is_url))
            self.history_index += 1

        self.update_navigation_buttons()

    def load_html_content(self, content):
        if content.startswith("http://") or content.startswith("https://"):
            self.html_frame.load_url(content)
            self.add_to_history(content, is_url=True)
        else:
            self.html_frame.load_html(content)
            self.add_to_history(content, is_url=False)

    def go_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            content, is_url = self.history[self.history_index]
            if is_url:
                self.html_frame.load_url(content)
            else:
                self.html_frame.load_html(content)
        self.update_navigation_buttons()

    def go_forward(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            content, is_url = self.history[self.history_index]
            if is_url:
                self.html_frame.load_url(content)
            else:
                self.html_frame.load_html(content)
        self.update_navigation_buttons()

    def update_navigation_buttons(self):
        self.back_button.configure(state="normal" if self.history_index > 0 else "disabled")
        self.forward_button.configure(state="normal" if self.history_index < len(self.history) - 1 else "disabled")

    def on_back_button(self, event):
        self.go_back()

    def on_forward_button(self, event):
        self.go_forward()

    def on_right_click(self, event):
        url = self.html_frame.get_current_link(resolve=True)
        if url:
            self.clipboard_clear()
            self.clipboard_append(url)
            self.parent.status(f"copied {url} to clipboard.")

class ScanResultsDialog(ctk.CTkToplevel):
    def __init__(self, parent, devices):
        super().__init__(parent)
        self.title("mDNS-SD - Select NETCONF Device")
        self.geometry("400x300")
        self.devices = devices
        self.selected_device = None

        self.listbox = Listbox(self)
        self.listbox.pack(fill="both", expand=True, padx=10, pady=10)
        self.update_listbox()

        self.cancel_button = ctk.CTkButton(self, text="Cancel",
                                           command=self.on_cancel)
        self.cancel_button.pack(side="left", padx=10, pady=10)

        self.ok_button = ctk.CTkButton(self, text="OK",
                                       command=self.on_ok)
        self.ok_button.pack(side="right", padx=10, pady=10)

        # Allow closing with common key bindings
        self.bind("<Control-w>", lambda event: self.destroy())
        self.bind("<Escape>", lambda event: self.destroy())
        # Bring frame into foreground and focus it when it becomes visible
        self.bind("<Map>", self.on_map)

    def on_map(self, event):
        self.lift()
        self.focus_force()

    def update_listbox(self):
        self.listbox.delete(0, END)
        for name, ip, port in self.devices:
            name = name.rstrip('.')
            self.listbox.insert('end', f"{name} - {ip}:{port}")

    def on_ok(self):
        selection = self.listbox.curselection()
        if selection:
            self.selected_device = self.devices[selection[0]]
        self.destroy()

    def on_cancel(self):
        self.destroy()
