from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.core.clipboard import Clipboard
import importlib
import pkgutil
import inspect

class AdvancedModuleExplorer(App):
    def build(self):
        self.theme_dark = False
        self.cheat_sheet_lines = []
        self.module_stack = []

        root = BoxLayout(orientation='vertical', spacing=5, padding=5)

        # --- Top bar: module input + explore + theme toggle ---
        top_bar = BoxLayout(size_hint_y=None, height=40, spacing=5)
        self.module_input = TextInput(hint_text="Enter module/package", size_hint_x=0.5)
        explore_btn = Button(text="Explore", size_hint_x=0.2)
        explore_btn.bind(on_press=self.explore_module)
        clear_btn = Button(text="Clear", size_hint_x=0.2)
        clear_btn.bind(on_press=self.clear_all)
        theme_btn = Button(text="Dark Mode", size_hint_x=0.1)
        theme_btn.bind(on_press=self.toggle_theme)
        top_bar.add_widget(self.module_input)
        top_bar.add_widget(explore_btn)
        top_bar.add_widget(clear_btn)
        top_bar.add_widget(theme_btn)

        # --- Middle panels: Left tree, Right items, Bottom cheat sheet ---
        middle_layout = BoxLayout()

        # Left panel: module tree
        self.tree_scroll = ScrollView(size_hint=(0.3, 1))
        self.tree_layout = GridLayout(cols=1, size_hint_y=None, spacing=5)
        self.tree_layout.bind(minimum_height=self.tree_layout.setter('height'))
        self.tree_scroll.add_widget(self.tree_layout)

        # Center panel: functions/classes/constants
        center_layout = BoxLayout(orientation='vertical', size_hint=(0.4,1))
        self.search_input = TextInput(hint_text="Search functions/classes", size_hint_y=None, height=40)
        self.search_input.bind(text=self.filter_items)
        self.items_scroll = ScrollView()
        self.items_layout = GridLayout(cols=1, size_hint_y=None, spacing=5)
        self.items_layout.bind(minimum_height=self.items_layout.setter('height'))
        self.items_scroll.add_widget(self.items_layout)
        center_layout.add_widget(self.search_input)
        center_layout.add_widget(self.items_scroll)

        # Right panel: live cheat sheet
        self.cheat_scroll = ScrollView(size_hint=(0.3, 1))
        self.cheat_layout = GridLayout(cols=1, size_hint_y=None, spacing=5)
        self.cheat_layout.bind(minimum_height=self.cheat_layout.setter('height'))
        self.cheat_scroll.add_widget(self.cheat_layout)

        middle_layout.add_widget(self.tree_scroll)
        middle_layout.add_widget(center_layout)
        middle_layout.add_widget(self.cheat_scroll)

        # Bottom bar: copy/save
        bottom_bar = BoxLayout(size_hint_y=None, height=50, spacing=5)
        copy_btn = Button(text="Copy Cheat Sheet")
        copy_btn.bind(on_press=self.copy_cheat_sheet)
        save_btn = Button(text="Save Cheat Sheet")
        save_btn.bind(on_press=self.save_cheat_sheet)
        bottom_bar.add_widget(copy_btn)
        bottom_bar.add_widget(save_btn)

        root.add_widget(top_bar)
        root.add_widget(middle_layout)
        root.add_widget(bottom_bar)

        return root

    # --- Clear all ---
    def clear_all(self, instance):
        self.tree_layout.clear_widgets()
        self.items_layout.clear_widgets()
        self.cheat_layout.clear_widgets()
        self.cheat_sheet_lines.clear()
        self.module_stack.clear()

    # --- Theme toggle ---
    def toggle_theme(self, instance):
        self.theme_dark = not self.theme_dark
        bg = [0.1,0.1,0.1,1] if self.theme_dark else [1,1,1,1]
        fg = [1,1,1,1] if self.theme_dark else [0,0,0,1]
        self.root.canvas.before.clear()
        with self.root.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*bg)
            Rectangle(pos=self.root.pos, size=self.root.size)

    # --- Explore module ---
    def explore_module(self, instance):
        self.tree_layout.clear_widgets()
        self.items_layout.clear_widgets()
        self.cheat_layout.clear_widgets()
        self.cheat_sheet_lines.clear()
        module_name = self.module_input.text.strip()
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            self.show_popup(f"Module '{module_name}' not found!")
            return
        self.add_tree_node(module_name, module)

    # --- Add tree node ---
    def add_tree_node(self, name, module, indent=0):
        btn = Button(text="  "*indent + name, size_hint_y=None, height=40)
        btn.bind(on_press=lambda inst, mod=module, mod_name=name: self.load_items(mod_name, mod))
        self.tree_layout.add_widget(btn)

        # Submodules
        if hasattr(module, "__path__"):
            for finder, sub_name, ispkg in pkgutil.iter_modules(module.__path__):
                try:
                    full_name = f"{name}.{sub_name}"
                    submodule = importlib.import_module(full_name)
                    self.add_tree_node(sub_name, submodule, indent=indent+1)
                except:
                    continue

    # --- Load items in center panel ---
    def load_items(self, mod_name, module):
        self.items_layout.clear_widgets()
        self.all_items = []
        for name in dir(module):
            if name.startswith("__"):
                continue
            try:
                obj = getattr(module, name)
                btn = Button(text=name, size_hint_y=None, height=40)
                btn.bind(on_press=lambda inst, obj=obj, stmt=f"from {mod_name} import {name}": self.show_item_popup(obj, stmt))
                self.items_layout.add_widget(btn)
                self.all_items.append((name, btn))
            except:
                continue

    # --- Search filter ---
    def filter_items(self, instance, text):
        for name, btn in getattr(self, "all_items", []):
            btn.opacity = 1 if text.lower() in name.lower() else 0
            btn.disabled = False if text.lower() in name.lower() else True

    # --- Show popup ---
    def show_item_popup(self, obj, stmt):
        doc = inspect.getdoc(obj) or "No documentation available"
        if inspect.isfunction(obj):
            try:
                sig = str(inspect.signature(obj))
            except:
                sig = "()"
            usage = f"{stmt}\n# Function: {obj.__name__}{sig}\n# Doc: {doc}"
        elif inspect.isclass(obj):
            try:
                sig = str(inspect.signature(getattr(obj, "__init__", None)))
            except:
                sig = "()"
            usage = f"{stmt}\n# Class: {obj.__name__}{sig}\n# Doc: {doc}"
        else:
            usage = stmt

        # Add to cheat sheet live
        self.cheat_sheet_lines.append(usage)
        lbl = Label(text=usage, size_hint_y=None)
        lbl.bind(texture_size=lbl.setter('size'))
        self.cheat_layout.add_widget(lbl)

        # Popup content
        popup_layout = BoxLayout(orientation='vertical', spacing=5, padding=5)
        scroll = ScrollView()
        label = Label(text=usage, size_hint_y=None)
        label.bind(texture_size=label.setter('size'))
        scroll.add_widget(label)
        popup_layout.add_widget(scroll)

        btn_layout = BoxLayout(size_hint_y=None, height=50, spacing=5)
        close_btn = Button(text="Close")
        popup = Popup(title=f"{obj.__class__.__name__} Info", content=popup_layout, size_hint=(0.9, 0.8))
        close_btn.bind(on_press=popup.dismiss)
        btn_layout.add_widget(close_btn)
        popup_layout.add_widget(btn_layout)

        popup.open()

    # --- Copy / Save ---
    def copy_cheat_sheet(self, instance):
        if self.cheat_sheet_lines:
            Clipboard.copy("\n\n".join(self.cheat_sheet_lines))
            self.show_popup("Cheat sheet copied to clipboard!")

    def save_cheat_sheet(self, instance):
        if not self.cheat_sheet_lines:
            self.show_popup("Cheat sheet is empty!")
            return
        file_name = self.module_input.text.strip().replace(".", "_") + "_cheatsheet.py"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write("\n\n".join(self.cheat_sheet_lines))
        self.show_popup(f"Cheat sheet saved as {file_name}")

    # --- Popup ---
    def show_popup(self, message):
        layout = BoxLayout(orientation='vertical', spacing=5, padding=5)
        scroll = ScrollView()
        label = Label(text=message, size_hint_y=None)
        label.bind(texture_size=label.setter('size'))
        scroll.add_widget(label)
        layout.add_widget(scroll)
        close_btn = Button(text="Close", size_hint_y=None, height=40)
        popup = Popup(title="Info", content=layout, size_hint=(0.9, 0.5))
        close_btn.bind(on_press=popup.dismiss)
        layout.add_widget(close_btn)
        popup.open()


if __name__ == "__main__":
    AdvancedModuleExplorer().run()

