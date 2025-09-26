import os
import gi
gi.require_version('AppIndicator3', '0.1')
from gi.repository import AppIndicator3, Gtk

def quit_app(_):
    Gtk.main_quit()

state = True
def toggle_icon(_):
    global state

    #folder where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    if state:
        indicator.set_icon_full(os.path.join(script_dir, "icon", "demo-ok.png"), "OK")
    else:
        indicator.set_icon_full(os.path.join(script_dir, "icon", "demo-bad.png"), "Bad")
    state = not state
    return True  # keep timer running

indicator = AppIndicator3.Indicator.new(
    "myapp-indicator",
    "system-run",  # an icon name from system theme, or absolute path to .png/.svg
    AppIndicator3.IndicatorCategory.APPLICATION_STATUS
)

indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

# Build a simple menu
menu = Gtk.Menu()

item_quit = Gtk.MenuItem(label="Quit")
item_quit.connect("activate", quit_app)
menu.append(item_quit)

item_toggle = Gtk.MenuItem(label="Toggle Icon")
item_toggle.connect("activate", toggle_icon)
menu.append(item_toggle)

menu.show_all()
indicator.set_menu(menu)

Gtk.main()
